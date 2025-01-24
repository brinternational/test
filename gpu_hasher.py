import pyopencl as cl
import numpy as np
from typing import List, Optional
import logging

class GPUHasher:
    # OpenCL kernel code remains unchanged
    KERNEL_CODE = """
    #define ROTRIGHT(word,bits) (((word) >> (bits)) | ((word) << (32-(bits))))
    #define CH(x,y,z) (((x) & (y)) ^ (~(x) & (z)))
    #define MAJ(x,y,z) (((x) & (y)) ^ ((x) & (z)) ^ ((y) & (z)))
    #define EP0(x) (ROTRIGHT(x,2) ^ ROTRIGHT(x,13) ^ ROTRIGHT(x,22))
    #define EP1(x) (ROTRIGHT(x,6) ^ ROTRIGHT(x,11) ^ ROTRIGHT(x,25))
    #define SIG0(x) (ROTRIGHT(x,7) ^ ROTRIGHT(x,18) ^ ((x) >> 3))
    #define SIG1(x) (ROTRIGHT(x,17) ^ ROTRIGHT(x,19) ^ ((x) >> 10))

    __kernel void sha256_batch(__global const uchar* input,
                           __global uint* output,
                           const uint batch_size,
                           const uint input_length) {
        int gid = get_global_id(0);
        if (gid >= batch_size) return;

        uint h0 = 0x6a09e667;
        uint h1 = 0xbb67ae85;
        uint h2 = 0x3c6ef372;
        uint h3 = 0xa54ff53a;
        uint h4 = 0x510e527f;
        uint h5 = 0x9b05688c;
        uint h6 = 0x1f83d9ab;
        uint h7 = 0x5be0cd19;

        uint w[64];
        uint offset = gid * input_length;

        for (int i = 0; i < 16; i++) {
            w[i] = (input[offset + 4*i] << 24) |
                   (input[offset + 4*i + 1] << 16) |
                   (input[offset + 4*i + 2] << 8) |
                   (input[offset + 4*i + 3]);
        }

        for (int i = 16; i < 64; i++) {
            w[i] = SIG1(w[i-2]) + w[i-7] + SIG0(w[i-15]) + w[i-16];
        }

        uint a = h0, b = h1, c = h2, d = h3;
        uint e = h4, f = h5, g = h6, h = h7;

        const uint k[64] = {
            0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5,
            0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
            0x243185be, 0x550c7dc3, 0x72be5d74, 0x80deb1fe,
            0x9bdc06a7, 0xc19bf174, 0xe49b69c1, 0xefbe4786,
            0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa,
            0x5cb0a9dc, 0x76f988da, 0x983e5152, 0xa831c66d,
            0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147,
            0x06ca6351, 0x14292967, 0x27b70a85, 0x2e1b2138,
            0x4d2c6dfc, 0x53380d13, 0x650a7354, 0x766a0abb,
            0x81c2c92e, 0x92722c85, 0xa2bfe8a1, 0xa81a664b,
            0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624,
            0xf40e3585, 0x106aa070, 0x19a4c116, 0x1e376c08,
            0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a,
            0x5b9cca4f, 0x682e6ff3, 0x748f82ee, 0x78a5636f,
            0x84c87814, 0x8cc70208, 0x90befffa, 0xa4506ceb,
            0xbef9a3f7, 0xc67178f2
        };

        for (int i = 0; i < 64; i++) {
            uint t1 = h + EP1(e) + CH(e,f,g) + k[i] + w[i];
            uint t2 = EP0(a) + MAJ(a,b,c);
            h = g; g = f; f = e;
            e = d + t1;
            d = c; c = b; b = a;
            a = t1 + t2;
        }

        output[gid*8] = h0 + a;
        output[gid*8 + 1] = h1 + b;
        output[gid*8 + 2] = h2 + c;
        output[gid*8 + 3] = h3 + d;
        output[gid*8 + 4] = h4 + e;
        output[gid*8 + 5] = h5 + f;
        output[gid*8 + 6] = h6 + g;
        output[gid*8 + 7] = h7 + h;
    }
    """

    def __init__(self, enable_cpu=True, enable_gpu=True, enable_npu=True, gpu_threads=256):
        self.ctx = None
        self.queue = None
        self.program = None
        self.device_type = None
        self.enable_cpu = enable_cpu
        self.enable_gpu = enable_gpu
        self.enable_npu = enable_npu
        self.gpu_threads = gpu_threads
        self.max_work_group_size = 256  # Will be updated based on device capabilities

        try:
            self._initialize_accelerator()
        except Exception as e:
            logging.warning(f"Hardware acceleration initialization failed: {str(e)}")
            # Set fallback to CPU-only mode
            self.device_type = "CPU"
            self.enable_gpu = False
            self.enable_npu = False

    def _detect_qualcomm_npu(self, platform) -> Optional[cl.Device]:
        """Detect Qualcomm NPU specifically."""
        try:
            for device in platform.get_devices():
                if any(id_str.lower() in device.name.lower() for id_str in ['qualcomm', 'qcom', 'adreno']):
                    if device.type == cl.device_type.ACCELERATOR:
                        logging.info(f"Detected Qualcomm NPU: {device.name}")
                        return device
            return None
        except:
            return None

    def _initialize_accelerator(self):
        """Initialize OpenCL context with improved error handling."""
        try:
            platforms = cl.get_platforms()
            if not platforms:
                raise RuntimeError("No OpenCL platforms available - falling back to CPU")

            selected_device = None
            platform = platforms[0]

            # Try each acceleration method in order of preference
            if self.enable_npu and not selected_device:
                try:
                    selected_device = self._detect_qualcomm_npu(platform)
                    if selected_device:
                        self.device_type = "NPU"
                        logging.info("NPU acceleration enabled")
                except:
                    logging.warning("NPU detection failed")

            if self.enable_gpu and not selected_device:
                try:
                    devices = platform.get_devices(device_type=cl.device_type.GPU)
                    if devices:
                        selected_device = devices[0]
                        self.device_type = "GPU"
                        logging.info("GPU acceleration enabled")
                except:
                    logging.warning("GPU detection failed")

            if self.enable_cpu and not selected_device:
                try:
                    devices = platform.get_devices(device_type=cl.device_type.CPU)
                    if devices:
                        selected_device = devices[0]
                        self.device_type = "CPU"
                        logging.info("CPU acceleration enabled")
                except:
                    logging.warning("CPU detection failed")

            if not selected_device:
                raise RuntimeError("No compatible acceleration devices found")

            # Initialize OpenCL context and queue
            self.ctx = cl.Context([selected_device])
            self.queue = cl.CommandQueue(self.ctx)
            self.program = cl.Program(self.ctx, self.KERNEL_CODE).build()
            self.max_work_group_size = min(256, selected_device.max_work_group_size)

            logging.info(f"Acceleration initialized on: {selected_device.name}")

        except Exception as e:
            logging.error(f"Acceleration initialization failed: {str(e)}")
            raise

    def _verify_device_capabilities(self, device):
        """Verify if device meets minimum requirements."""
        try:
            min_memory = 128 * 1024 * 1024  
            if device.global_mem_size < min_memory:
                raise RuntimeError(f"Insufficient device memory: {device.global_mem_size / (1024*1024):.2f} MB")

            if device.max_compute_units < 1:
                raise RuntimeError("Device has no compute units")

            version = device.version.split()
            if len(version) >= 2:
                major, minor = map(int, version[1].split('.'))
                if major < 1 or (major == 1 and minor < 1):
                    raise RuntimeError(f"OpenCL version {version[1]} not supported. Minimum required: 1.2")

        except Exception as e:
            logging.error(f"Device capability verification failed: {str(e)}")
            raise

    def set_gpu_threads(self, thread_count: int):
        """Update GPU thread count within device limits."""
        if self.ctx and self.device_type in ("GPU", "NPU"):
            device = self.ctx.devices[0]
            # Ensure thread count doesn't exceed device limits
            self.gpu_threads = min(thread_count, device.max_compute_units * 64)
            self.max_work_group_size = min(256, device.max_work_group_size)
            logging.info(f"GPU threads set to {self.gpu_threads} (max work group size: {self.max_work_group_size})")

    def compute_hash_batch(self, data_batch: List[bytes], input_length: int = 64) -> List[bytes]:
        """Compute SHA256 hashes optimized for GPU processing."""
        if not self.ctx:
            raise RuntimeError("Hardware acceleration not initialized")

        try:
            batch_size = len(data_batch)

            # Optimize work group size based on device type
            if self.device_type == "GPU":
                local_size = min(self.max_work_group_size, 256)
            else:
                local_size = min(self.max_work_group_size, 64)

            # Calculate optimal global size
            global_size = max(
                ((batch_size + local_size - 1) // local_size) * local_size,
                self.gpu_threads
            )

            input_buffer = np.zeros((batch_size, input_length), dtype=np.uint8)
            for i, data in enumerate(data_batch):
                input_buffer[i, :len(data)] = np.frombuffer(data, dtype=np.uint8)

            output_buffer = np.zeros((batch_size, 32), dtype=np.uint32)

            # Use multiple command queues for better parallelism on GPU
            num_queues = 2 if self.device_type == "GPU" else 1
            queues = [cl.CommandQueue(self.ctx) for _ in range(num_queues)]

            # Split work across multiple queues
            split_points = [(i * batch_size) // num_queues for i in range(num_queues + 1)]
            results = []

            for q_idx in range(num_queues):
                start, end = split_points[q_idx], split_points[q_idx + 1]
                if start == end:
                    continue

                input_gpu = cl.Buffer(
                    self.ctx,
                    cl.mem_flags.READ_ONLY | cl.mem_flags.COPY_HOST_PTR,
                    hostbuf=input_buffer[start:end]
                )
                output_gpu = cl.Buffer(
                    self.ctx,
                    cl.mem_flags.WRITE_ONLY,
                    size=output_buffer[start:end].nbytes
                )

                try:
                    # Execute kernel with optimized work group size
                    self.program.sha256_batch(
                        queues[q_idx],
                        (global_size,),
                        (local_size,),
                        input_gpu,
                        output_gpu,
                        np.uint32(end - start),
                        np.uint32(input_length)
                    )

                    # Copy results back
                    cl.enqueue_copy(queues[q_idx], output_buffer[start:end], output_gpu)

                finally:
                    input_gpu.release()
                    output_gpu.release()

            # Convert results to bytes
            for i in range(batch_size):
                hash_value = output_buffer[i].tobytes()
                results.append(hash_value)

            return results

        except cl.RuntimeError as e:
            logging.error(f"OpenCL error in hash computation: {str(e)}")
            raise

    @classmethod
    def is_accelerator_available(cls) -> bool:
        """Check if hardware acceleration (NPU/GPU) is available."""
        try:
            platform = cl.get_platforms()[0]
            devices = platform.get_devices(device_type=cl.device_type.ACCELERATOR)
            if not devices:
                devices = platform.get_devices(device_type=cl.device_type.GPU)
            return bool(devices)
        except:
            return False

    def get_device_info(self) -> Optional[str]:
        """Get detailed information about the current OpenCL device."""
        if not self.ctx:
            return None

        device = self.ctx.devices[0]
        return (
            f"{self.device_type} Device: {device.name}\n"
            f"Version: {device.version}\n"
            f"Compute Units: {device.max_compute_units}\n"
            f"GPU Threads: {self.gpu_threads}\n"
            f"Work Group Size: {self.max_work_group_size}\n"
            f"Global Memory: {device.global_mem_size / (1024*1024):.2f} MB\n"
            f"Local Memory: {device.local_mem_size / 1024:.2f} KB"
        )