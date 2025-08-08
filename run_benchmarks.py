#!/usr/bin/env python3
import argparse
import os
import subprocess
import toml
import shutil
import time
from pathlib import Path
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='[%(asctime)s - %(levelname)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

def get_time_control(water_box_str, iteration, use_profiling, rules):
    """
    Determines the time control arguments for gmx mdrun by reading rules from the config.
    """
    if use_profiling:
        return "-nsteps 400", False

    try:
        box_float = float(water_box_str.lstrip('0'))
    except ValueError:
        logging.warning(f"Could not parse water_box value: {water_box_str}. No rules will match.")
        return "", True # Return empty string and skip run

    for rule in rules:
        if box_float <= rule.get('max_box_size', 0):
            time_control = f"-nsteps {rule['nsteps']} --resetstep {rule['resetstep']}"
            
            skip_run = False
            iteration_cutoff = rule.get('iteration_cutoff')
            if iteration_cutoff and iteration > iteration_cutoff:
                skip_run = True
            
            return time_control, skip_run

    logging.warning(f"No matching time control rule found for water_box: {water_box_str}")
    return "", True # Default to skipping if no rule is found


def check_convergence(outfile: Path):
    """
    Checks the output file for the 'kernel_cache' string to see if JIT optimization is complete.
    Returns True if converged, False otherwise.
    """
    if not outfile.is_file():
        return False
    try:
        with open(outfile, 'r') as f:
            return "kernel_cache" not in f.read()
    except IOError as e:
        logging.error(f"Could not read outfile {outfile}: {e}")
        return False

def run_gmx_command(command, cwd, env, outfile, log_file):
    """
    Executes a GROMACS command, redirecting its output to a file.
    Raises CalledProcessError if the command returns a non-zero exit code.
    """
    logging.info(f"Running command: {' '.join(command)}")
    logging.info(f"Working directory: {cwd}")
    logging.info(f"Output file: {outfile}")
    
    with open(log_file, 'w') as f_log:
        try:
            process = subprocess.run(
                command,
                cwd=cwd,
                env=env,
                stdout=f_log,
                stderr=subprocess.STDOUT,
                text=True,
                check=False
            )
            if process.returncode != 0:
                with open(log_file, 'r') as f_read:
                    log_tail = "".join(f_read.readlines()[-20:])
                
                error_message = (
                    f"Command exited with non-zero code: {process.returncode}.\n"
                    f"Check full logs at: {log_file}\n"
                    f"--- Last 20 lines of log ---\n{log_tail}"
                )
                logging.error(error_message)
                raise subprocess.CalledProcessError(process.returncode, command, output=error_message)

        except FileNotFoundError:
            error_message = f"Command not found: {command[0]}. Is GROMACS installed and in the PATH?"
            logging.error(error_message)
            raise
        except Exception as e:
            logging.error(f"An unexpected error occurred while running the command: {e}")
            raise


def main():
    """
    Main function to parse arguments, load config, and run the benchmark suite.
    """
    parser = argparse.ArgumentParser(
        description="Run GROMACS benchmarks based on a TOML configuration file.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument('--config', type=Path, default='config.toml', help='Path to the main build definition TOML file.')
    parser.add_argument('--bench-config', type=Path, required=True, help='Path to the benchmark-specific TOML file.')
    parser.add_argument('--dirname', type=str, required=True, help='Name for the root benchmark results directory.')
    parser.add_argument('--profile', action='store_true', help='Enable profiling mode.')
    parser.add_argument('--profile-serialize', action='store_true', help='Enable serialized profiling (implies --profile).')

    args = parser.parse_args()

    if args.profile_serialize:
        args.profile = True

    # --- Load Configuration Files ---
    if not args.config.is_file():
        logging.error(f"Main configuration file not found at: {args.config}")
        exit(1)
    if not args.bench_config.is_file():
        logging.error(f"Benchmark configuration file not found at: {args.bench_config}")
        exit(1)
    
    config = toml.load(args.config)
    bench_config_data = toml.load(args.bench_config)
    bench_params = bench_config_data.get('benchmark', {})
    
    logging.info(f"Loaded build definitions from: {args.config}")
    logging.info(f"Loaded benchmark parameters from: {args.bench_config}")

    # --- Setup Benchmark Parameters from Config ---
    ncpu = bench_params.get('ncpu', 32)
    iteration_num = bench_params.get('profile_iterations', 1) if args.profile else bench_params.get('iterations', 5)
    flavors = bench_params.get('flavors', [])
    water_boxes = bench_params.get('water_boxes', [])
    time_control_rules = bench_params.get('time_control_rules', [])
    env_vars = bench_params.get('environment', {})
    variants_to_run = bench_params.get('variants_to_run', [])
    adaptivity_levels_to_check = bench_params.get('adaptivity_levels_to_check', [])
    
    # --- Validate required configuration keys ---
    if not variants_to_run:
        logging.error("The 'variants_to_run' key in the benchmark config cannot be empty. Please specify which variants to run.")
        exit(1)
    if not adaptivity_levels_to_check:
        logging.error("The 'adaptivity_levels_to_check' key in the benchmark config cannot be empty.")
        exit(1)
    if not all([flavors, water_boxes, time_control_rules, env_vars]):
        logging.error("One or more required keys (flavors, water_boxes, time_control_rules, environment) are missing from the [benchmark] section of the benchmark config.")
        exit(1)

    # --- Setup Paths ---
    gmx_root_dir = Path.cwd()
    gmx_water_benchmark_root_dir = gmx_root_dir / bench_params.get("water_box_source_dir", "grappa-1.5k-6.1M_rc0.9")
    benchmark_out_root = gmx_root_dir / "benchmark_results" / args.dirname
    
    # --- Clean ACPP Cache ---
    acpp_cache = Path.home() / ".acpp"
    if acpp_cache.exists():
        logging.info(f"Removing existing ACPP cache at {acpp_cache}")
        shutil.rmtree(acpp_cache)

    # --- Create a lookup map for GROMACS variants for efficient access ---
    gromacs_variants_map = {v['name']: v for v in config.get('gromacs_variants', [])}

    logging.info(f"Will run the following specified variants: {variants_to_run}")

    # --- Main Benchmark Loop ---
    for i in range(1, iteration_num + 1):
        logging.info(f"--- Starting Iteration {i}/{iteration_num} ---")
        
        for variant in variants_to_run:
            variant_name = variant['name']
            gmx_variant = gromacs_variants_map.get(variant['name'])
            gmx_variant['run_fft'] = variant.get('run_fft', False) 
            if not gmx_variant:
                logging.error(f"GROMACS variant '{variant_name}' specified in benchmark config was not found in main config '{args.config}'.")
                exit(-1)
            
            if gmx_variant.get('adaptive', False):
                levels_to_iterate = adaptivity_levels_to_check
            else:
                levels_to_iterate = [None] # Run only once without adaptivity

            for level in levels_to_iterate:
                # --- Set Environment for this Specific Run ---
                run_env = os.environ.copy()
                for key, value in env_vars.items():
                    if key.endswith("_PREFIX"):
                        base_key = key.removesuffix("_PREFIX")
                        run_env[base_key] = f"{value}{run_env.get(base_key, '')}"
                    else:
                        run_env[key] = str(value)

                if level is not None:
                    run_env["ACPP_ADAPTIVITY_LEVEL"] = str(level)
                    level_str = f"_al{level}"
                else:
                    level_str = ""

                # --- Construct Paths for this Run ---
                build_dir = Path("/") / gmx_variant['directory'] / "build"
                gmx_executable = build_dir / "bin" / "gmx"
                benchmark_out_dir_name = f"{gmx_variant['name']}{level_str}"
                benchmark_out_path = benchmark_out_root / benchmark_out_dir_name
                
                logging.info(f"\nProcessing GROMACS variant: {gmx_variant['name']} (Adaptivity Level: {level or 'N/A'})")

                for flavor in flavors:
                    logging.info(f"  Flavor: {flavor}")
                    pme = "auto" if flavor == "rf" else "gpu"

                    for water_box in water_boxes:
                        time_control_args, skip_run = get_time_control(water_box, i, args.profile, time_control_rules)
                        if skip_run:
                            logging.info(f"    Skipping water_box {water_box} for iteration {i} based on config rules.")
                            continue
                        
                        logging.info(f"    Water Box: {water_box}")
                        
                        benchmark_out_path_water = benchmark_out_path / water_box / flavor
                        benchmark_out_path_water.mkdir(parents=True, exist_ok=True)
                        
                        tpr_file = gmx_water_benchmark_root_dir / water_box / flavor / "water.tpr"
                        if not tpr_file.is_file():
                            logging.warning(f"      TPR file not found, skipping: {tpr_file}")
                            continue

                        # --- Determine PME FFT setting based on the variant's config ---
                        pmefft_setting = "gpu" if gmx_variant.get('run_fft') else "cpu"

                        # --- Convergence Loop ---
                        has_converged = False
                        num_runs = 0
                        while not has_converged:
                            num_runs += 1
                            logging.info(f"      Convergence run #{num_runs}...")
                            
                            outfile_conv = benchmark_out_path_water / f"out_convergence_{num_runs}.log"
                            cmd_conv = [
                                str(gmx_executable), "mdrun", "-noconfout", "-nb", "gpu", "-bonded", "gpu", 
                                "-update", "gpu", "-pme", pme, "-pmefft", pmefft_setting, "-ntmpi", "1", 
                                "-ntomp", str(ncpu), "-s", str(tpr_file)
                            ]
                            # Use the calculated time control arguments for the convergence run
                            cmd_conv.extend(time_control_args.split())
                            
                            run_gmx_command(cmd_conv, cwd=benchmark_out_path_water, env=run_env, outfile=outfile_conv, log_file=outfile_conv)
                            
                            has_converged = check_convergence(outfile_conv)
                            if has_converged:
                                logging.info("      JIT-Optimization complete.")
                            else:
                                logging.info("      Still optimizing...")
                                md_log = benchmark_out_path_water / "md.log"
                                if md_log.exists():
                                    md_log.unlink()

                        # --- Final Timed/Profiled Run ---
                        # The convergence loop already performed the final run, so we only need to
                        # handle the special case for profiling.
                        if args.profile:
                            logging.info(f"      Running final profiled benchmark...")
                            outfile_final = benchmark_out_path_water / f"out_final_iter_{i}.log"
                            base_cmd = [
                                str(gmx_executable), "mdrun", "-notunepme", "-noconfout", "-nb", "gpu", 
                                "-bonded", "gpu", "-update", "gpu", "-pme", pme, "-pmefft", pmefft_setting, 
                                "-ntmpi", "1", "-ntomp", str(ncpu), "-s", str(tpr_file)
                            ]
                            base_cmd.extend(time_control_args.split())
                            
                            prof_env = run_env.copy()
                            if args.profile_serialize:
                                prof_env["AMD_SERIALIZE_COPY"] = "3"
                                prof_env["AMD_SERIALIZE_KERNEL"] = "3"
                            
                            profile_cmd = ["/opt/rocm/bin/rocprofv2", "--kernel-trace", "--plugin", "file", "-o", "kernel_trace"]
                            profile_cmd.extend(base_cmd)
                            run_gmx_command(profile_cmd, cwd=benchmark_out_path_water, env=prof_env, outfile=outfile_final, log_file=outfile_final)

if __name__ == "__main__":
    main()