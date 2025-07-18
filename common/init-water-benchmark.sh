#!/bin/bash -xe 
source environment.sh

ROOT_DIR=`pwd`
GMX_BIN_DIR=/gromacs-sscp-builtins/build/bin/

wget https://zenodo.org/records/11234002/files/grappa-1.5k-6.1M_rc0.9.tar.gz?download=1
tar xvf grappa-1.5k-6.1M_rc0.9.tar.gz\?download\=1
tar xvf kernel-flavor-test-mdps.tar.gz

mdps_folder=mdps
cd grappa-1.5k-6.1M_rc0.9


for problem in 0000.96  0001.5  0003  0006  0012  0024  0048  0096  0192  0384  0768  1536  3072 6144
do
  for flavor in rf psh fsw psw 
  do
    mkdir -p $problem/$flavor
  $GMX_BIN_DIR/gmx grompp -f /$mdps_folder/grompp-$flavor.mdp -c $problem/conf.gro -r $problem/conf.gro -p $problem/topol.top -o $problem/$flavor/water.tpr
done
done

