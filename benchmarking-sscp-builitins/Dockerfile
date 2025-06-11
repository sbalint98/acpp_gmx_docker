FROM rocm/dev-ubuntu-24.04:6.4.1

RUN apt -y update
RUN apt -y install cmake git gnupg lsb-release software-properties-common vim wget ninja-build lz4 pax-utils valgrind python3-pip
#RUN apt -y install rocm-validation-suite

#Install boost dependcies  
RUN apt-get -y install libboost-context-dev libboost-fiber-dev libboost-filesystem-dev libboost-test-dev 

RUN apt -y install libfftw3-dev

ARG LLVM_VERSION=19
#Add LLVM 15 repo  
RUN wget https://apt.llvm.org/llvm.sh  
RUN bash ./llvm.sh $LLVM_VERSION  

#Install libclang  
RUN apt-get -y install libclang-$LLVM_VERSION-dev libclang-$LLVM_VERSION-dev clang-tools-$LLVM_VERSION libomp-$LLVM_VERSION-dev  

RUN apt -y install ssh openssh-server 


RUN apt -y install nginx
COPY --chmod=755 start.sh /
COPY --chmod=755 post_start.sh /
COPY --chmod=755 init-water-benchmark.sh /

ADD git@github.com:sbalint98/AdaptiveCpp.git#bsoproni-all-gmx-builtins-benchmark ./AdaptiveCpp

# GMX variants
ADD git@gitlab.com:sbalint98/gromacs.git#benchmark-base ./gromacs-smcp
ADD git@gitlab.com:sbalint98/gromacs.git#sb-rel25-sscp-enable-upstream-benchmark ./gromacs-sscp-base
ADD git@gitlab.com:sbalint98/gromacs.git#enable-sscp-builtins-benchmark ./gromacs-sscp-builtins

# GMX HIP b9a54af63e5964be0612260083a5757ef51df16e
ADD git@github.com:ROCm/Gromacs#4947-hip-feature-enablement-2025.2 ./gromacs-hip


RUN cmake -GNinja -S ./AdaptiveCpp/ -B ./AdaptiveCpp/build/ 
RUN ninja -C ./AdaptiveCpp/build 
RUN cmake --install ./AdaptiveCpp/build/ 

ARG GENERAL_CMAKE_OPTIONS=" -DCMAKE_BUILD_TYPE=Release "

ARG ACPP_CMAKE_OPTIONS=" $GENERAL_CMAKE_OPTIONS -DCMAKE_C_COMPILER=clang-$LLVM_VERSION \
                         -DCMAKE_CXX_COMPILER=clang++-$LLVM_VERSION \
			 -DCMAKE_BUILD_TYPE=Release "


RUN apt -y install  roctracer-dev rocprofiler-dev roctracer-dev
ENV ROCM_PATH=/opt/rocm/

RUN cmake -GNinja -S ./gromacs-sscp-base -B ./gromacs-sscp-base/build $ACPP_CMAKE_OPTIONS \
                  -D GMX_GPU=SYCL \
                  -D GMX_SYCL=ACPP \
                  -D ACPP_TARGETS=generic \
                  -D GMX_GPU_FFT_LIBRARY=none \
		  -D GMX_USE_ROCTX=ON

RUN cmake -GNinja -S ./gromacs-sscp-builtins -B ./gromacs-sscp-builtins/build $ACPP_CMAKE_OPTIONS \
                  -D GMX_GPU=SYCL \
                  -D GMX_SYCL=ACPP \
                  -D ACPP_TARGETS=generic \
                  -D GMX_GPU_FFT_LIBRARY=none \
		  -D GMX_USE_ROCTX=ON
                
RUN cmake -GNinja -S ./gromacs-smcp -B ./gromacs-smcp/build $ACPP_CMAKE_OPTIONS \
                  -D GMX_GPU=SYCL \
                  -D GMX_SYCL=ACPP \
                  -D ACPP_TARGETS="hip:gfx906,gfx908,gfx90a,gfx940" \
                  -D GMX_GPU_FFT_LIBRARY=none \
		  -D GMX_USE_ROCTX=ON


RUN apt -y install rocprim-dev libamdhip64-dev librocprim-dev
RUN cmake -GNinja -S ./gromacs-hip -B ./gromacs-hip/build $GENERAL_CMAKE_OPTIONS \
                  -D CMAKE_C_COMPILER=hipcc \
                  -D CMAKE_CXX_COMPILER=hipcc \
                  -D GMX_GPU=HIP \
                  -D GMX_HIP_TARGET_ARCH="gfx906,gfx908,gfx90a,gfx940" \
		  -D GMX_USE_ROCTX=ON
##
#						  -DCMAKE_C_COMPILER=clang-$LLVM_VERSION \
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
#
#RUN cmake --install ./gromacs/build
#RUN bash init-water-benchmark.sh


#CMD ["/start.sh"]
