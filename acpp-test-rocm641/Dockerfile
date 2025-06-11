FROM rocm/dev-ubuntu-24.04:6.4.1
RUN apt -y update
RUN apt -y install cmake git gnupg lsb-release software-properties-common vim wget ninja-build lz4 pax-utils valgrind python3-pip
RUN apt -y install rocm-validation-suite

#Install boost dependcies  
RUN apt-get -y install libboost-context-dev libboost-fiber-dev libboost-filesystem-dev libboost-test-dev 
RUN apt -y install libfftw3-dev

ARG LLVM_VERSION=17
RUN wget https://apt.llvm.org/llvm.sh  
RUN bash ./llvm.sh $LLVM_VERSION  
RUN apt-get -y install libclang-$LLVM_VERSION-dev libclang-$LLVM_VERSION-dev clang-tools-$LLVM_VERSION libomp-$LLVM_VERSION-dev  

#Needed For Runpod
RUN apt -y install ssh openssh-server 
RUN apt -y install nginx
#COPY --chmod=755 start.sh /
#COPY --chmod=755 post_start.sh /
#COPY --chmod=755 init-water-benchmark.sh /

ADD git@github.com:AdaptiveCpp/AdaptiveCpp.git#v25.02.0 ./AdaptiveCpp
ADD git@gitlab.com:sbalint98/gromacs.git#sb-rel25-sscp-enable-upstream ./gromacs

RUN cmake -GNinja -S ./AdaptiveCpp/ -B ./AdaptiveCpp/build/ 
RUN ninja -C ./AdaptiveCpp/build 
RUN cmake --install ./AdaptiveCpp/build/ 

RUN cmake -GNinja -S ./AdaptiveCpp/tests -B ./AdaptiveCpp/tests/build  
RUN ninja -C ./AdaptiveCpp/tests/build 


#RUN cmake -GNinja -S ./gromacs -B ./gromacs/build -DCMAKE_C_COMPILER=clang-$LLVM_VERSION \
#                                                  -DCMAKE_CXX_COMPILER=clang++-$LLVM_VERSION \
#                                                  -DGMX_GPU=SYCL \
#						  -DGMX_SYCL_HIPSYCL=ON \
#						  -DGMX_ACPP_HAVE_GENERIC_TARGET=ON \
#                                                  -DGMX_GPU_FFT_LIBRARY=none \
#                                                  -DHIPSYCL_TARGETS=generic \
#					          -DBUILD_TESTING=ON \	
#                                                  -DREGRESSIONTEST_DOWNLOAD=ON 
#RUN ninja -C ./gromacs/build
#RUN ninja -C ./gromacs/build tests

#RUN cmake --install ./gromacs/build
#RUN bash init-water-benchmark.sh

