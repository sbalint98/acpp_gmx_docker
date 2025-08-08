import toml
import sys
import subprocess
#import dataclass
from dataclasses import dataclass
from jinja2 import Environment, FileSystemLoader

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
            acpp_variants.append(variant)


        # 2. Iterate through GROMACS variants (this part is unchanged)
        gmx_variants = []
        for gmx in config.get('gromacs_variants', []):
            gmx_name = gmx['name']
            acpp_name = gmx.get('acpp_variant')

            if not acpp_name or acpp_name not in resolved_acpp:
                raise ValueError(f"GROMACS variant '{gmx_name}' references an unknown ACPP variant '{acpp_name}'.")

            gmx_repos_to_search = [r for r in gmx_repos if r['name'] == gmx['repo']] if 'repo' in gmx else gmx_repos
            gmx_commit = resolve_commit(gmx['branch'], gmx_repos_to_search)
            gmx['commit'] = gmx_commit.commit_hash
            gmx['repo'] = gmx_commit.repo
            gmx['acpp_install_root'] = resolved_acpp[acpp_name]['directory']
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
