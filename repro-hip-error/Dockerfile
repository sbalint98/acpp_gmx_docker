FROM rocm/dev-ubuntu-24.04:6.4.1

RUN apt -y update
RUN apt -y install cmake git gnupg lsb-release software-properties-common vim wget ninja-build lz4 pax-utils valgrind python3-pip libfftw3-dev ssh 
# Additonal ROCM packages needed
RUN apt -y install rocprim-dev libamdhip64-dev librocprim-dev

# GMX HIP b9a54af63e5964be0612260083a5757ef51df16e
ADD git@github.com:ROCm/Gromacs#4947-hip-feature-enablement-2025.2 ./gromacs-hip



ARG GENERAL_CMAKE_OPTIONS=" -D CMAKE_BUILD_TYPE=Release \
                            -D BUILD_TESTING=ON \ 
                            -D GMX_SIMD=AVX2_128 \
                            -D REGRESSIONTEST_DOWNLOAD=ON "

RUN cmake -GNinja -S ./gromacs-hip -B ./gromacs-hip/build $GENERAL_CMAKE_OPTIONS \
                  -D CMAKE_C_COMPILER=hipcc \
                  -D CMAKE_CXX_COMPILER=hipcc \
                  -D GMX_GPU=HIP \
                  -D GMX_HIP_TARGET_ARCH="gfx90a" 

RUN ninja -C ./gromacs-hip/build tests
RUN ninja -C ./gromacs-hip/build gmx
