dirs=(
    "gromacs-sscp-final-cdna"
    "gromacs-sscp-final-rdna"
    "gromacs-sscp-all-arch-cdna"
    "gromacs-sscp-builtins-cdna"
    "gromacs-sscp-cdna"
    "gromacs-smcp-cdna"
    "gromacs-thesis-base-cdna"
    "gromacs-smcp-acpp-base-gmx-allarch-cdna/"
    "gromacs-smcp-acpp-base-gmx-final-cdna/"
    "gromacs-smcp-allarch-cdna"
    "gromacs-smcp-final-cdna"
    "gromacs-smcp-final-rdna"
    "gromacs-hip"
)

for dir in "${dirs[@]}"; do
  cd /$dir/build/ && ninja check 2>&1 | tee  /$dir-check-results.out
done

