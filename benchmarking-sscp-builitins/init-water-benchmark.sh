#!/bin/bash -xe 
source environment.sh

ROOT_DIR=`pwd`
GMX_BIN_DIR=/gromacs/build/bin/

wget https://ftp.gromacs.org/benchmarks/water_bare_hbonds.tar.gz
tar xvf water_bare_hbonds.tar.gz
cd water-cut1.0_bare_hbonds

for problem in 0000.96  0001.5  0003  0006  0012  0024  0048  0096  0192  0384  0768  1536  3072
do
  $GMX_BIN_DIR/gmx grompp -f $problem/pme.mdp -c $problem/conf.gro -r $problem/conf.gro -p $problem/topol.top -o $problem/water.tpr
done

