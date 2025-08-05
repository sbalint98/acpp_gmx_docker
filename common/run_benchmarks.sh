#!/bin/bash 
set -e

USE_PROFILING=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        --profile)
            USE_PROFILING=true
            shift
            ;;
         --profile-serialize)
            USE_PROFILING=true
            PROFILE_SERIALIZE=true
            shift
            ;;
        --dirname)
            if [[ -n "$2" && "$2" != --* ]]; then
                DIRNAME="$2"
                shift 2
            else
                echo "Error: --dirname requires a non-empty argument."
                exit 1
            fi
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

ncpu=32

gmx_root_dir=`pwd`
gmx_water_benchmark_root_dir=`pwd`/grappa-1.5k-6.1M_rc0.9
benchmark_out_root=`pwd`/benchmark_results/$DIRNAME

export ACPP_PERSISTENT_RUNTIME=1 
export ACPP_DEBUG_LEVEL=2
export LD_LIBRARY_PATH=/opt/rocm/lib/:$LD_LIBRARY_PATH 
export PATH=/opt/rocm/bin/:$PATH
export ACPP_VISIBILITY_MASK=hip

iteration_num=5
if [ "$USE_PROFILING" = true ]; then
        iteration_num=1
fi

rm -rf ~/.acpp/

for i in $(seq 1 $iteration_num)
do
    for gromacs_build in sscp-builtins-al1 sscp-builtins-al2 smcp 
    do
      for flavor in rf fsw psh psw 
      do
        case $gromacs_build in 
             sscp-base-al1)
                export ACPP_ADAPTIVITY_LEVEL=1
                build_dir=/gromacs-sscp-base/build
                benchmark_out_dir="sscp_base_al${ACPP_ADAPTIVITY_LEVEL}_${BASE_REPO_VERSION}_acpp_${ACPP_FORK_VERSION}_gmx_${GMX_FORK_VERSION}"
                ;;
             sscp-base-al2)
                export ACPP_ADAPTIVITY_LEVEL=2
                build_dir=/gromacs-sscp-base/build
                benchmark_out_dir="sscp_base_al${ACPP_ADAPTIVITY_LEVEL}_${BASE_REPO_VERSION}_acpp_${ACPP_FORK_VERSION}_gmx_${GMX_FORK_VERSION}"
                ;;
            sscp-builtins-al1)
                export ACPP_ADAPTIVITY_LEVEL=1
                build_dir=/gromacs-sscp-builtins/build
                benchmark_out_dir="sscp_builtins_al${ACPP_ADAPTIVITY_LEVEL}_${BASE_REPO_VERSION}_acpp_${ACPP_FORK_VERSION}_gmx_${GMX_FORK_VERSION}"
                ;;
    
            sscp-builtins-al2)
                export ACPP_ADAPTIVITY_LEVEL=2
                build_dir=/gromacs-sscp-builtins/build
                benchmark_out_dir="sscp_builtins_al${ACPP_ADAPTIVITY_LEVEL}_${BASE_REPO_VERSION}_acpp_${ACPP_FORK_VERSION}_gmx_${GMX_FORK_VERSION}"
                ;;
            hip)
                build_dir=/gromacs-hip/build
                benchmark_out_dir="hip_${BASE_REPO_VERSION}_acpp_${ACPP_UPSTREAM_VERSION}_gmx_${GMX_UPSTREAM_VERSION}"
                ;;
            smcp)
                build_dir=/gromacs-smcp/build
                benchmark_out_dir="smcp_${BASE_REPO_VERSION}_acpp_${ACPP_UPSTREAM_VERSION}_gmx_${GMX_UPSTREAM_VERSION}"
                ;;
            smcp-psplit)
                build_dir=/gromacs-smcp/build-psplit
                benchmark_out_dir="smcp_psplit${BASE_REPO_VERSION}_acpp_${ACPP_UPSTREAM_VERSION}_gmx_${GMX_UPSTREAM_VERSION}"
                ;;
        esac
        benchmark_out_path=$benchmark_out_root/$benchmark_out_dir
        benchmark_test_out_path=$benchmark_out_root/$benchmark_out_dir/test_results.out
    
    
        echo $benchmark_out_path
        pme=gpu
        if [ "$flavor" == "rf" ]; then
                pme=auto
        fi
        for water_box in  0001.5  0003  0006  0012  0024  0048 0096  0192  0384  0768  1536  3072 #6144
            do
            box_value=$(echo "$water_box" | sed 's/^0*//')
            box_float=$(printf "%.4f" "$box_value")
            skip_run=false

            if (( $(echo "$box_float <= 6" | bc -l) )); then
                time_control="-nsteps 200000 --resetstep 160000"
            elif (( $(echo "$box_float <= 48" | bc -l) )); then
                time_control="-nsteps 100000 --resetstep 80000"
            elif (( $(echo "$box_float <= 96" | bc -l) )); then
                time_control="-nsteps 50000 --resetstep 40000"
            elif (( $(echo "$box_float <= 192" | bc -l) )); then
                time_control="-nsteps 15000 --resetstep 12000"
            elif (( $(echo "$box_float <= 1536" | bc -l) )); then
               if (( i > 3 )); then
                  skip_run=true
               fi
               time_control="-nsteps 10000 --resetstep 8000"
            else
               if (( i > 3 )); then
                  skip_run=true
               fi
               time_control="-nsteps 5000 --resetstep 4000"
            fi


            benchmark_out_path_water=$benchmark_out_path/$water_box/$flavor
            benchmark_out_path_water_host=$benchmark_out_path_water
            has_converged=false
            num_runs=1

            while [ "$has_converged" != true ]
            do
              echo "[run-benchmark.sh] Running..."
              set -e
              mkdir -p $benchmark_out_path
              mkdir -p $benchmark_out_path_water
              export ACPP_DEBUG_LEVEL=$ACPP_DEBUG_LEVEL
              export ACPP_ADAPTIVITY_LEVEL=$ACPP_ADAPTIVITY_LEVEL
              export ACPP_VISIBILITY_MASK=$ACPP_VISIBILITY_MASK
              export LD_LIBRARY_PATH=/opt/rocm/lib/:$LD_LIBRARY_PATH
              cd $benchmark_out_path_water
              outfile=$benchmark_out_path_water_host/out_$i.out
              if [ "$USE_PROFILING" = false ] ; then
                if  [ "$skip_run" = false ] ; then
                echo running e2e $water_box $flavor
                start_time=$(date +%s)
                $build_dir/bin/gmx mdrun $time_control -noconfout -nb gpu -bonded gpu  -update gpu  -pme $pme -pmefft cpu -ntmpi 1 -ntomp $ncpu -s $gmx_water_benchmark_root_dir/$water_box/$flavor/water.tpr &> $outfile
                end_time=$(date +%s)
                duration=$((end_time - start_time))
                echo " Took $duration s at: `date`"
                fi
              else
                $build_dir/bin/gmx mdrun  -notunepme -noconfout -nb gpu -bonded gpu  -update gpu  -pme $pme -pmefft cpu -ntmpi 1 -ntomp $ncpu  -nsteps 400  -s $gmx_water_benchmark_root_dir/$water_box/$flavor/water.tpr &> $outfile
              fi
              #echo $outfile          
              set +e
              grep "kernel_cache" $outfile > /dev/null
              if [ $? = 0 ] ; then
              set -e
                echo "Stil optimizing..."
                rm $benchmark_out_path_water_host/md.log
              else
                echo "JIT-Optimization complete."
                has_converged=true
                echo "#final-num-runs $num_runs" >> $outfile
            if [ "$USE_PROFILING" = true ]; then
                    echo "Profiling run"
                    set -e
                    mkdir -p $benchmark_out_path
                    mkdir -p $benchmark_out_path_water
                    export ACPP_DEBUG_LEVEL=$ACPP_DEBUG_LEVEL
                    export ACPP_ADAPTIVITY_LEVEL=$ACPP_ADAPTIVITY_LEVEL
                    export ACPP_VISIBILITY_MASK=$ACPP_VISIBILITY_MASK
                    export LD_LIBRARY_PATH=/opt/rocm/lib/:$LD_LIBRARY_PATH
            if [ "$PROFILE_SERIALIZE" = true ]; then
                    export AMD_SERIALIZE_COPY=3 
                    export AMD_SERIALIZE_KERNEL=3
            fi
                    export PATH=/opt/rocm/bin/:$PATH
                    cd $benchmark_out_path_water
                     /opt/rocm/bin/rocprofv2 --kernel-trace --plugin file -o kernel_trace  $build_dir/bin/gmx mdrun -notunepme -noconfout -nb gpu -bonded gpu  -update gpu  -pme $pme -pmefft cpu -ntmpi 1 -ntomp $ncpu  -nsteps 400  -s $gmx_water_benchmark_root_dir/$water_box/$flavor/water.tpr 2>&1 &>  out_$i.out
                fi
              fi
            done
        echo $flavor
        done
        echo $water_box
      done
    done 
done

