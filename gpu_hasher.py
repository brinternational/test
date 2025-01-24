import pyopencl as cl
import numpy as np
from typing import List, Optional
import logging

class GPUHasher:
    # OpenCL kernel code
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
        self.max_work_group_size = 256
        self.platform_info = None
        self.available_devices = []

        try:
            self._initialize_accelerator()
        except Exception as e:
            logging.error(f"GPU initialization failed: {str(e)}")
            self._fallback_to_cpu()

    def _detect_available_platforms(self):
        """Detect all available OpenCL platforms and their devices."""
        try:
            platforms = cl.get_platforms()
            platform_info = []

            for platform in platforms:
                try:
                    platform_name = platform.name
                    platform_version = platform.version
                    devices = []

                    # Try to get all types of devices
                    for device_type in [cl.device_type.GPU, cl.device_type.CPU, cl.device_type.ACCELERATOR]:
                        try:
                            platform_devices = platform.get_devices(device_type=device_type)
                            for device in platform_devices:
                                device_info = {
                                    'name': device.name,
                                    'type': device_type,
                                    'vendor': device.vendor,
                                    'version': device.version,
                                    'compute_units': device.max_compute_units,
                                    'global_mem': device.global_mem_size,
                                    'local_mem': device.local_mem_size,
                                    'max_work_group_size': device.max_work_group_size
                                }
                                devices.append(device_info)
                                self.available_devices.append(device)
                        except:
                            continue

                    platform_info.append({
                        'name': platform_name,
                        'version': platform_version,
                        'devices': devices
                    })
                except:
                    continue

            return platform_info
        except:
            return []

    def _initialize_accelerator(self):
        """Initialize OpenCL with improved platform and device detection."""
        try:
            platform_info = self._detect_available_platforms()
            if not platform_info:
                logging.warning("No OpenCL platforms detected")
                self._fallback_to_cpu()
                return

            # Log detailed platform information
            for platform in platform_info:
                logging.info(f"\nPlatform: {platform['name']} ({platform['version']})")
                for device in platform['devices']:
                    logging.info(f"  Device: {device['name']}")
                    logging.info(f"    Type: {device['type']}")
                    logging.info(f"    Vendor: {device['vendor']}")
                    logging.info(f"    Compute Units: {device['compute_units']}")

            # Try to find the best device
            selected_device = None

            # First, try to find Qualcomm GPU
            if self.enable_gpu:
                selected_device = self._find_qualcomm_device()

            # If no Qualcomm device, try other GPUs
            if not selected_device and self.enable_gpu:
                selected_device = self._find_best_gpu()

            # Finally, fall back to CPU if needed
            if not selected_device and self.enable_cpu:
                selected_device = self._find_cpu_device()

            if not selected_device:
                logging.warning("No suitable compute device found")
                self._fallback_to_cpu()
                return

            # Initialize OpenCL context and command queue
            self.ctx = cl.Context([selected_device])
            self.queue = cl.CommandQueue(self.ctx)
            self.program = cl.Program(self.ctx, self.KERNEL_CODE).build()

            # Update device configuration
            self.max_work_group_size = min(256, selected_device.max_work_group_size)
            self.device_type = "GPU" if selected_device.type in [cl.device_type.GPU, cl.device_type.ACCELERATOR] else "CPU"

            logging.info(f"Successfully initialized {self.device_type} acceleration")
            logging.info(f"Selected device: {selected_device.name}")
            logging.info(f"Work group size: {self.max_work_group_size}")
            logging.info(f"Compute units: {selected_device.max_compute_units}")

        except Exception as e:
            logging.error(f"Accelerator initialization failed: {str(e)}")
            self._fallback_to_cpu()

    def _find_qualcomm_device(self) -> Optional[cl.Device]:
        """Find Qualcomm GPU/NPU device."""
        for device in self.available_devices:
            try:
                vendor = device.vendor.lower()
                name = device.name.lower()
                if ('qualcomm' in vendor or 'qualcomm' in name or 
                    'qcom' in vendor or 'qcom' in name or
                    'adreno' in vendor or 'adreno' in name):
                    if device.type in [cl.device_type.GPU, cl.device_type.ACCELERATOR]:
                        return device
            except:
                continue
        return None

    def _find_best_gpu(self) -> Optional[cl.Device]:
        """Find the best available GPU device."""
        best_device = None
        max_compute_units = 0

        for device in self.available_devices:
            try:
                if device.type == cl.device_type.GPU:
                    if device.max_compute_units > max_compute_units:
                        best_device = device
                        max_compute_units = device.max_compute_units
            except:
                continue

        return best_device

    def _find_cpu_device(self) -> Optional[cl.Device]:
        """Find a CPU device for fallback."""
        for device in self.available_devices:
            try:
                if device.type == cl.device_type.CPU:
                    return device
            except:
                continue
        return None

    def _fallback_to_cpu(self):
        """Handle fallback to CPU-only mode."""
        self.device_type = "CPU"
        self.enable_gpu = False
        self.enable_npu = False
        logging.warning("Falling back to CPU-only mode")

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