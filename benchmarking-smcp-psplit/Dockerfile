FROM rocm/dev-ubuntu-24.04:6.4.1

RUN apt -y update
RUN apt -y install cmake git gnupg lsb-release software-properties-common vim wget ninja-build lz4 pax-utils valgrind python3-pip libboost-context-dev libboost-fiber-dev libboost-filesystem-dev libboost-test-dev libfftw3-dev ssh openssh-server nginx roctracer-dev rocprofiler-dev roctracer-dev gdb debuginfod hip-runtime-amd-dbgsym

ARG LLVM_SMCP_VERSION=19
ARG ACPP_VERSION=github.com:AdaptiveCpp/AdaptiveCpp.git#v25.02.0


RUN wget https://apt.llvm.org/llvm.sh  
RUN bash ./llvm.sh $LLVM_SMCP_VERSION  

RUN apt-get -y install libclang-$LLVM_SMCP_VERSION-dev libclang-$LLVM_SMCP_VERSION-dev clang-tools-$LLVM_SMCP_VERSION libomp-$LLVM_SMCP_VERSION-dev  

ADD git@$ACPP_VERSION ./AdaptiveCpp

ADD git@gitlab.com:sbalint98/gromacs.git#benchmark-base ./gromacs-smcp


RUN cmake -GNinja -S ./AdaptiveCpp/ -B ./AdaptiveCpp/build-smcp/ \
                   -DCMAKE_BUILD_TYPE=Release \
                   -DLLVM_DIR=/usr/lib/llvm-$LLVM_SMCP_VERSION/lib/cmake/llvm/
RUN ninja -C ./AdaptiveCpp/build-smcp 
RUN cmake --install ./AdaptiveCpp/build-smcp/ --prefix=/AdaptiveCpp/build-smcp/install 


ARG GENERAL_CMAKE_OPTIONS=" -D CMAKE_BUILD_TYPE=Release \
		                        -D GMX_USE_ROCTX=ON \
                            -D BUILD_TESTING=ON \ 
                            -D GMX_SIMD=AVX2_128 \
                            -D REGRESSIONTEST_DOWNLOAD=ON "

ARG ACPP_CMAKE_OPTIONS=" $GENERAL_CMAKE_OPTIONS \ 
                         -D GMX_GPU_FFT_LIBRARY=VkFFT \
                         -D GMX_GPU=SYCL \
                         -D GMX_SYCL=ACPP "

RUN apt -y install  roctracer-dev rocprofiler-dev roctracer-dev
ENV ROCM_PATH=/opt/rocm/

RUN cmake -GNinja -S ./gromacs-smcp -B ./gromacs-smcp/build $ACPP_CMAKE_OPTIONS \
                  -D CMAKE_C_COMPILER=clang-$LLVM_SMCP_VERSION \
                  -D CMAKE_CXX_COMPILER=clang++-$LLVM_SMCP_VERSION  \
                  -D CMAKE_PREFIX_PATH=/AdaptiveCpp/build-smcp/install/lib/cmake/AdaptiveCpp \
                  -D ACPP_TARGETS="hip:gfx906,gfx908,gfx90a,gfx940,gfx942" 

RUN cmake -GNinja -S ./gromacs-smcp -B ./gromacs-smcp/build-psplit $ACPP_CMAKE_OPTIONS \
                  -D CMAKE_C_COMPILER=clang-$LLVM_SMCP_VERSION \
                  -D CMAKE_CXX_COMPILER=clang++-$LLVM_SMCP_VERSION  \
                  -D GMX_GPU_NB_DISABLE_CLUSTER_PAIR_SPLIT=OFF \
                  -D CMAKE_PREFIX_PATH=/AdaptiveCpp/build-smcp/install/lib/cmake/AdaptiveCpp \
                  -D ACPP_TARGETS="hip:gfx906,gfx908,gfx90a,gfx940,gfx942" 

RUN apt -y install  libamdhip64-dev rocm-cmake

RUN ninja -C ./gromacs-smcp/build tests
RUN ninja -C ./gromacs-smcp/build gmx
RUN ninja -C ./gromacs-smcp/build-psplit tests
RUN ninja -C ./gromacs-smcp/build-psplit gmx

COPY common/kernel-flavor-test-mdps.tar.gz /
COPY --chmod=755 common/init-water-benchmark.sh /
RUN bash init-water-benchmark.sh
COPY --chmod=755 common/start.sh /
COPY --chmod=755 common/post_start.sh /
COPY --chmod=755 common/run_benchmarks.sh /

