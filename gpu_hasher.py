import pyopencl as cl
import numpy as np
from typing import List, Optional
import logging

class GPUHasher:
    # OpenCL kernel for SHA256 computation
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

        // Initialize hash values
        uint h0 = 0x6a09e667;
        uint h1 = 0xbb67ae85;
        uint h2 = 0x3c6ef372;
        uint h3 = 0xa54ff53a;
        uint h4 = 0x510e527f;
        uint h5 = 0x9b05688c;
        uint h6 = 0x1f83d9ab;
        uint h7 = 0x5be0cd19;

        // Process message
        uint w[64];
        uint offset = gid * input_length;
        
        // First 16 words are message itself
        for (int i = 0; i < 16; i++) {
            w[i] = (input[offset + 4*i] << 24) |
                   (input[offset + 4*i + 1] << 16) |
                   (input[offset + 4*i + 2] << 8) |
                   (input[offset + 4*i + 3]);
        }

        // Extend to 64 words
        for (int i = 16; i < 64; i++) {
            w[i] = SIG1(w[i-2]) + w[i-7] + SIG0(w[i-15]) + w[i-16];
        }

        // Main loop
        uint a = h0, b = h1, c = h2, d = h3;
        uint e = h4, f = h5, g = h6, h = h7;
        
        const uint k[64] = {
            0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5,
            0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
            // ... (rest of k array)
        };

        for (int i = 0; i < 64; i++) {
            uint t1 = h + EP1(e) + CH(e,f,g) + k[i] + w[i];
            uint t2 = EP0(a) + MAJ(a,b,c);
            h = g; g = f; f = e;
            e = d + t1;
            d = c; c = b; b = a;
            a = t1 + t2;
        }

        // Output final hash for this batch item
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

    def __init__(self):
        self.ctx = None
        self.queue = None
        self.program = None
        self._initialize_gpu()

    def _initialize_gpu(self):
        """Initialize OpenCL context and compile kernel."""
        try:
            platform = cl.get_platforms()[0]
            devices = platform.get_devices(device_type=cl.device_type.GPU)
            
            if not devices:  # Fallback to CPU if no GPU available
                devices = platform.get_devices(device_type=cl.device_type.CPU)
                logging.warning("No GPU found, falling back to CPU for OpenCL")
            
            self.ctx = cl.Context(devices)
            self.queue = cl.CommandQueue(self.ctx)
            self.program = cl.Program(self.ctx, self.KERNEL_CODE).build()
            logging.info(f"GPU acceleration initialized on: {devices[0].name}")
            
        except Exception as e:
            logging.error(f"Failed to initialize GPU acceleration: {str(e)}")
            self.ctx = None
            raise

    def compute_hash_batch(self, data_batch: List[bytes], input_length: int = 64) -> List[bytes]:
        """Compute SHA256 hashes for a batch of inputs using GPU."""
        if not self.ctx:
            raise RuntimeError("GPU acceleration not initialized")

        try:
            batch_size = len(data_batch)
            
            # Prepare input buffer
            input_buffer = np.zeros((batch_size, input_length), dtype=np.uint8)
            for i, data in enumerate(data_batch):
                input_buffer[i, :len(data)] = np.frombuffer(data, dtype=np.uint8)

            # Create output buffer
            output_buffer = np.zeros((batch_size, 32), dtype=np.uint32)

            # Transfer data to GPU
            input_gpu = cl.Buffer(self.ctx, cl.mem_flags.READ_ONLY | cl.mem_flags.COPY_HOST_PTR,
                                hostbuf=input_buffer)
            output_gpu = cl.Buffer(self.ctx, cl.mem_flags.WRITE_ONLY, output_buffer.nbytes)

            # Execute kernel
            self.program.sha256_batch(self.queue, (batch_size,), None,
                                    input_gpu, output_gpu,
                                    np.uint32(batch_size),
                                    np.uint32(input_length))

            # Get results
            cl.enqueue_copy(self.queue, output_buffer, output_gpu)
            
            # Convert to bytes
            results = []
            for i in range(batch_size):
                hash_value = output_buffer[i].tobytes()
                results.append(hash_value)

            return results

        except cl.RuntimeError as e:
            logging.error(f"OpenCL error in hash computation: {str(e)}")
            raise
        finally:
            # Clean up GPU buffers
            if 'input_gpu' in locals():
                input_gpu.release()
            if 'output_gpu' in locals():
                output_gpu.release()

    @classmethod
    def is_gpu_available(cls) -> bool:
        """Check if GPU acceleration is available."""
        try:
            platform = cl.get_platforms()[0]
            devices = platform.get_devices(device_type=cl.device_type.GPU)
            return bool(devices)
        except:
            return False

    def get_device_info(self) -> Optional[str]:
        """Get information about the current OpenCL device."""
        if not self.ctx:
            return None
        
        device = self.ctx.devices[0]
        return f"{device.name} ({device.version})"
