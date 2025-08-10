import toml
import sys
import subprocess
#import dataclass
from dataclasses import dataclass
from jinja2 import Environment, FileSystemLoader
import os 
import json

@dataclass
class commit:
    repo: str
    commit_hash:str

def resolve_commit(ref_name, repos_to_search) -> commit:
    """
    Searches a list of repositories for a branch OR a tag and returns the commit hash.
    Raises an error if the reference is not found or is ambiguous.
    """
    found_commits = []
    for repo in repos_to_search:
        repo_name = repo['name']
        repo_url = repo['url']
        for ref_type in ["heads", "tags"]:
            try:
                result = subprocess.check_output(
                    ['git', 'ls-remote', repo_url, f"refs/{ref_type}/{ref_name}"],
                    text=True, stderr=subprocess.DEVNULL
                ).strip()
                if result:
                    commit_hash = result.split()[0]
                    if repo_name in found_commits and found_commits[repo_name] != commit_hash:
                         raise ValueError(f"Ambiguous reference '{ref_name}' in repo '{repo_name}'.")
                    found_commits.append(commit(repo=repo_url, commit_hash=commit_hash))
            except subprocess.CalledProcessError:
                continue
    if not found_commits: raise ValueError(f"Reference '{ref_name}' not found.")
    if len(found_commits) > 1: raise ValueError(f"Ambiguous reference '{ref_name}'.")
    return found_commits[0]

def check_if_value_already_exists(field_name, value, items):
    for i in items:
        if i.get(field_name) == value:
            raise ValueError(f"Duplicate {field_name} '{value}'. Please ensure all {field_name}s are unique.")


def get_needed_presets(preset, type):
    return_paths = []
    folder = ''

    if type == 'acpp':
        folder = os.path.join('presets', 'acpp')
    elif type == 'gromacs':
        folder = os.path.join('presets', 'gmx')
    else:
        raise ValueError(f"Unknown type '{type}'. Expected 'acpp' or 'gromacs'.")

    current_file_path = os.path.join(folder, f"{preset}.json")

    if os.path.exists(current_file_path):
        return_paths.append(current_file_path)
        search_paths = []

        try:
            with open(current_file_path, 'r') as f:
                data = json.load(f)

            if 'include' in data and isinstance(data['include'], list):
                for included_preset in data['include']:
                    search_paths.append(os.path.join(folder, included_preset))
                while search_paths:
                    next_preset = search_paths.pop(0)
                    next_file_path = next_preset#os.path.join(folder, next_preset)
                    if os.path.exists(next_file_path):
                        with open(next_file_path, 'r') as f:
                            # get the directory of next_file_path
                            folder = os.path.dirname(next_file_path)
                            included_data = json.load(f)
                        return_paths.append(next_file_path)
                        if 'include' in included_data and isinstance(included_data['include'], list):
                            for include in included_data['include']:
                                search_paths.append(os.path.join(folder,include))
                    else:
                        raise ValueError(f"Included preset '{next_preset}' not found in {next_file_path}.")

        except (json.JSONDecodeError, IOError) as e:
            raise ValueError(f"Warning: Could not read or parse {current_file_path}. Error: {e}")
    else:
        raise ValueError(f"Preset file '{current_file_path}' does not exist.")
    return_paths = list(dict.fromkeys(return_paths))
    needed_presets = [os.path.relpath(p, start=os.getcwd()) for p in return_paths]
    final = [(needed_presets[0], "CMakeUserPresets.json")]
    for preset in needed_presets[1:]:
        if type == "gromacs":
            final.append((preset, preset.replace("presets/gmx/", "")))
        else:
            final.append((preset, preset.replace("presets/acpp/", "")))
    return final

def main(file_path):
    try:
        with open(file_path, 'r') as f:
            config = toml.load(f)

        all_repos = config.get('repositories', {})
        acpp_repos = all_repos.get('acpp', [])
        gmx_repos = all_repos.get('gromacs', [])
        build_args = []

        # 1. Resolve all ACPP variants first and store them for lookup
        resolved_acpp = {}
        acpp_variants = []
        for variant in config.get('acpp_variants', []):
            name = variant['name']
            repos_to_search = [r for r in acpp_repos if r['name'] == variant['repo']] if 'repo' in variant else acpp_repos
            commit = resolve_commit(variant['branch'], repos_to_search)
            variant['commit'] = commit.commit_hash
            variant['repo'] = commit.repo
            resolved_acpp[name] = { 'commit': commit, **variant }
            check_if_value_already_exists('name', name, acpp_variants)
            check_if_value_already_exists('directory', variant['directory'], acpp_variants)
            needed_presets = get_needed_presets(variant['cmake_preset'], 'acpp')
            variant['needed_presets'] = needed_presets
            acpp_variants.append(variant)


        # 2. Iterate through GROMACS variants (this part is unchanged)
        gmx_variants = []
        for gmx in config.get('gromacs_variants', []):
            is_hip = gmx.get('hip', False)
            if is_hip:  
                continue
            gmx_name = gmx['name']
            acpp_name = gmx.get('acpp_variant')

            if not acpp_name or acpp_name not in resolved_acpp:
                raise ValueError(f"GROMACS variant '{gmx_name}' references an unknown ACPP variant '{acpp_name}'.")

            gmx_repos_to_search = [r for r in gmx_repos if r['name'] == gmx['repo']] if 'repo' in gmx else gmx_repos
            gmx_commit = resolve_commit(gmx['branch'], gmx_repos_to_search)
            gmx['commit'] = gmx_commit.commit_hash
            gmx['repo'] = gmx_commit.repo
            gmx['acpp_install_root'] = resolved_acpp[acpp_name]['directory']
            check_if_value_already_exists('name', gmx_name, gmx_variants)
            check_if_value_already_exists('directory', gmx['directory'], gmx_variants)
            preset_type = gmx["cmake_preset"]
            needed_presets = get_needed_presets(preset_type, 'gromacs')
            gmx['needed_presets'] = needed_presets
            gmx_variants.append(gmx)    


        # 3. Render the Dockerfile from the template
        env = Environment(loader=FileSystemLoader('.'), trim_blocks=True, lstrip_blocks=True)
        template = env.get_template('Dockerfile.template')
        dockerfile_content = template.render(
            acpp_variants=acpp_variants,
            gromacs_variants=gmx_variants
        )
        # 4. Print the final command to pipe the Dockerfile into docker build
        image_tag = "gmx-benchmarks:latest"
        build_args_str = ' '.join(build_args)
        
        print(dockerfile_content)
    except (ValueError, FileNotFoundError) as e:
        print(f"\nBuild Plan Failed: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"Usage: python3 {sys.argv[0]} <toml_file>", file=sys.stderr)
        sys.exit(1)
    main(sys.argv[1])
