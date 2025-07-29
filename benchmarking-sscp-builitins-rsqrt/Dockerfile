FROM rocm/dev-ubuntu-24.04:6.4.1

RUN apt -y update
RUN apt -y install cmake git gnupg lsb-release software-properties-common vim wget ninja-build lz4 pax-utils valgrind python3-pip
#RUN apt -y install rocm-validation-suite

#Install boost dependcies  
RUN apt-get -y install libboost-context-dev libboost-fiber-dev libboost-filesystem-dev libboost-test-dev 
RUN apt -y install libfftw3-dev

ARG LLVM_SSCP_VERSION=17
#rocm 6.4.1 reports 19.0.0git but it fails to compile with 18 so we need 19
ARG LLVM_SMCP_VERSION=19

RUN wget https://apt.llvm.org/llvm.sh  
RUN bash ./llvm.sh $LLVM_SSCP_VERSION  
RUN apt-get -y install libclang-$LLVM_SSCP_VERSION-dev libclang-$LLVM_SSCP_VERSION-dev clang-tools-$LLVM_SSCP_VERSION 

RUN bash ./llvm.sh $LLVM_SMCP_VERSION  
# SMCP compiler is later than SSCP therfore  we use their omp
RUN apt-get -y install libclang-$LLVM_SMCP_VERSION-dev libclang-$LLVM_SMCP_VERSION-dev clang-tools-$LLVM_SMCP_VERSION libomp-$LLVM_SMCP_VERSION-dev  

# Link back the SMCP LLVM OpenMP for the SSCP OpenMP

RUN ln -s /usr/lib/llvm-$LLVM_SMCP_VERSION/lib/clang/$LLVM_SMCP_VERSION/include/omp-tools.h /usr/lib/llvm-$LLVM_SSCP_VERSION/lib/clang/$LLVM_SSCP_VERSION/include/omp-tools.h
RUN ln -s /usr/lib/llvm-$LLVM_SMCP_VERSION/lib/clang/$LLVM_SMCP_VERSION/include/omp.h      /usr/lib/llvm-$LLVM_SSCP_VERSION/lib/clang/$LLVM_SSCP_VERSION/include/omp.h
RUN ln -s /usr/lib/llvm-$LLVM_SMCP_VERSION/lib/clang/$LLVM_SMCP_VERSION/include/ompt-multiplex.hlex.h /usr/lib/llvm-$LLVM_SSCP_VERSION/lib/clang/$LLVM_SSCP_VERSION/include/ompt-multiplex.hlex.h
RUN ln -s /usr/lib/llvm-$LLVM_SMCP_VERSION/lib/clang/$LLVM_SMCP_VERSION/include/ompt.h     /usr/lib/llvm-$LLVM_SSCP_VERSION/lib/clang/$LLVM_SSCP_VERSION/include/ompt.h
RUN ln -s /usr/lib/llvm-$LLVM_SMCP_VERSION/lib/clang/$LLVM_SMCP_VERSION/include/ompx.h     /usr/lib/llvm-$LLVM_SSCP_VERSION/lib/clang/$LLVM_SSCP_VERSION/include/ompx.h

RUN ln -s /usr/lib/llvm-$LLVM_SMCP_VERSION/lib/libomptarget.so /usr/lib/llvm-$LLVM_SSCP_VERSION/lib/libomptarget.so
RUN ln -s /usr/lib/llvm-$LLVM_SMCP_VERSION/lib/libgomp.so     /usr/lib/llvm-$LLVM_SSCP_VERSION/lib/libgomp.so
RUN ln -s /usr/lib/llvm-$LLVM_SMCP_VERSION/lib/libiomp5.so    /usr/lib/llvm-$LLVM_SSCP_VERSION/lib/libiomp5.so
RUN ln -s /usr/lib/llvm-$LLVM_SMCP_VERSION/lib/libomp.so      /usr/lib/llvm-$LLVM_SSCP_VERSION/lib/libomp.so


RUN apt -y install ssh openssh-server 
RUN apt -y install nginx

ARG ACPP_VERSION=github.com:sbalint98/AdaptiveCpp.git#bsoproni-all-gmx-builtins-benchmark-rsqrt


ADD git@$ACPP_VERSION ./AdaptiveCpp

# GMX variants
ADD git@gitlab.com:sbalint98/gromacs.git#benchmark-base ./gromacs-smcp
ADD git@gitlab.com:sbalint98/gromacs.git#sb-rel25-sscp-enable-upstream-benchmark ./gromacs-sscp-base
ADD git@gitlab.com:sbalint98/gromacs.git#enable-sscp-builtins-benchmark ./gromacs-sscp-builtins

# GMX HIP b9a54af63e5964be0612260083a5757ef51df16e
ADD git@github.com:ROCm/Gromacs#4947-hip-feature-enablement-2025.2 ./gromacs-hip


RUN cmake -GNinja -S ./AdaptiveCpp/ -B ./AdaptiveCpp/build-smcp/ \
                   -DLLVM_DIR=/usr/lib/llvm-$LLVM_SMCP_VERSION/lib/cmake/llvm/
RUN ninja -C ./AdaptiveCpp/build-smcp 
RUN cmake --install ./AdaptiveCpp/build-smcp/ --prefix=/AdaptiveCpp/build-smcp/install 

RUN cmake -GNinja -S ./AdaptiveCpp/ -B ./AdaptiveCpp/build-sscp/ \
                   -DLLVM_DIR=/usr/lib/llvm-$LLVM_SSCP_VERSION/lib/cmake/llvm/
RUN ninja -C ./AdaptiveCpp/build-sscp 
RUN cmake --install ./AdaptiveCpp/build-sscp/ --prefix=/AdaptiveCpp/build-sscp/install 

ARG GENERAL_CMAKE_OPTIONS=" -D CMAKE_BUILD_TYPE=Release \
		                        -D GMX_USE_ROCTX=ON \
                            -D BUILD_TESTING=ON \ 
                            -D GMX_SIMD=AVX2_128 \
                            -D REGRESSIONTEST_DOWNLOAD=ON "

ARG ACPP_CMAKE_OPTIONS=" $GENERAL_CMAKE_OPTIONS \ 
                         -D GMX_GPU_FFT_LIBRARY=none \
                         -D GMX_GPU=SYCL \
                         -D GMX_SYCL=ACPP "


RUN apt -y install  roctracer-dev rocprofiler-dev roctracer-dev
ENV ROCM_PATH=/opt/rocm/

RUN cmake  -GNinja -S ./gromacs-sscp-base -B ./gromacs-sscp-base/build $ACPP_CMAKE_OPTIONS \
                  -D CMAKE_C_COMPILER=clang-$LLVM_SSCP_VERSION \
                  -D CMAKE_CXX_COMPILER=clang++-$LLVM_SSCP_VERSION  \
                  -D CMAKE_PREFIX_PATH=/AdaptiveCpp/build-sscp/install/lib/cmake/AdaptiveCpp \
                  -D ACPP_TARGETS=generic 

RUN cmake -GNinja -S ./gromacs-sscp-builtins -B ./gromacs-sscp-builtins/build $ACPP_CMAKE_OPTIONS \
                  -D CMAKE_C_COMPILER=clang-$LLVM_SSCP_VERSION \
                  -D CMAKE_CXX_COMPILER=clang++-$LLVM_SSCP_VERSION  \
                  -D CMAKE_PREFIX_PATH=/AdaptiveCpp/build-sscp/install/lib/cmake/AdaptiveCpp \
                  -D ACPP_TARGETS=generic 
                

RUN cmake -GNinja -S ./gromacs-smcp -B ./gromacs-smcp/build $ACPP_CMAKE_OPTIONS \
                  -D CMAKE_C_COMPILER=clang-$LLVM_SMCP_VERSION \
                  -D CMAKE_CXX_COMPILER=clang++-$LLVM_SMCP_VERSION  \
                  -D CMAKE_PREFIX_PATH=/AdaptiveCpp/build-smcp/install/lib/cmake/AdaptiveCpp \
                  -D ACPP_TARGETS="hip:gfx906,gfx908,gfx90a,gfx940,gfx942" 


RUN apt -y install  libamdhip64-dev rocm-cmake

#Install rocprim
ADD git@github.com:ROCm/rocPRIM#rocm-6.4.1 ./rocprim 
RUN cmake -G Ninja -S ./rocprim -B ./rocprim/build \
                  -D CMAKE_C_COMPILER=hipcc \
                  -D CMAKE_CXX_COMPILER=hipcc 
RUN ninja -C ./rocprim/build
RUN cmake --install ./rocprim/build --prefix ./rocprim/build/install

ADD git@gitlab.com:sbalint98/gromacs.git#enable-sscp-builtins-benchmark ./gromacs-sscp-builtins

RUN cmake -GNinja -S ./gromacs-hip -B ./gromacs-hip/build $GENERAL_CMAKE_OPTIONS \
                  -D CMAKE_C_COMPILER=hipcc \
                  -D CMAKE_CXX_COMPILER=hipcc \
                  -D CMAKE_CXX_FLAGS="-I /rocprim/build/install/include/" \
                  -D GMX_GPU=HIP \
                  -D GMX_HIP_TARGET_ARCH="gfx906,gfx908,gfx90a,gfx940,gfx942" \
                  -D CMAKE_PREFIX_PATH=/rocprim/build/install/

RUN ninja -C ./gromacs-sscp-base/build tests
RUN ninja -C ./gromacs-sscp-builtins/build tests
RUN ninja -C ./gromacs-smcp/build tests
#RUN ninja -C ./gromacs-hip/build tests

RUN ninja -C ./gromacs-sscp-base/build gmx
RUN ninja -C ./gromacs-sscp-builtins/build gmx
RUN ninja -C ./gromacs-smcp/build gmx
#RUN ninja -C ./gromacs-hip/build gmx
COPY common/kernel-flavor-test-mdps.tar.gz /
COPY --chmod=755 common/init-water-benchmark.sh /
RUN bash init-water-benchmark.sh
COPY --chmod=755 common/start.sh /
COPY --chmod=755 common/post_start.sh /
COPY --chmod=755 common/run_benchmarks.sh /

RUN apt -y install gdb debuginfod hip-runtime-amd-dbgsym
