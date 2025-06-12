#!/bin/bash -xe 
source environment.sh

ROOT_DIR=`pwd`
GMX_BIN_DIR=/gromacs-sscp-base/build/bin/

wget https://zenodo.org/records/11234002/files/grappa-1.5k-6.1M_rc0.9.tar.gz?download=1
tar xvf grappa-1.5k-6.1M_rc0.9.tar.gz\?download\=1
cd grappa-1.5k-6.1M_rc0.9


for problem in 0000.96  0001.5  0003  0006  0012  0024  0048  0096  0192  0384  0768  1536  3072 6144
do
  $GMX_BIN_DIR/gmx grompp -f $problem/../pme.mdp -c $problem/conf.gro -r $problem/conf.gro -p $problem/topol.top -o $problem/water.tpr
done

