using System.Diagnostics;
using System.Runtime.InteropServices;
using System.Text;

namespace Nikke.Engine.Gpu;

public sealed record GpuPrimitiveResult(string Device,string Vendor,string Driver,bool SupportsFp64,
    string Status,int ValuesChecked,double ElapsedMilliseconds,string Reason)
{
    public string Backend => "opencl";
    public string KernelVersion => "fp64-hit-boundary.1";
    public bool FullBattleEligible => false;
    public string FullBattleStatus => "not_implemented";
}

// Experimental probe, never registered as a full-battle backend. Run only in a timeout-isolated process.
// Original implementation against Khronos OpenCL C/API, no vendored library or driver installation.
public static class OpenClPrimitiveProbe
{
    private const string Kernel="""
    #pragma OPENCL EXTENSION cl_khr_fp64 : enable
    #pragma OPENCL FP_CONTRACT OFF
    __kernel void probe(__global const double* input, __global double* output) {
      size_t i=get_global_id(0); double x=input[i];
      output[6*i]=floor(x);
      output[6*i+1]=rint(x);
      double magnitude=fabs(x),whole=floor(magnitude);
      output[6*i+2]=copysign(whole+(magnitude-whole>=0.5?1.0:0.0),x);
      double p=(100000.0-30925.0)*3.5+x;
      double terms=floor(p)+floor(p*0.5)+floor(p*1.0);
      output[6*i+3]=floor(terms*1.121*1.15*1.1);
      output[6*i+4]=floor(floor(floor(terms*1.121)*1.15)*1.1);
      output[6*i+5]=fmax(1.0,rint(p*2.5*1.121*1.15*1.1));
    }
    """;
    public static IReadOnlyList<GpuPrimitiveResult> RunInIsolatedProcess()
    {
        if(!OperatingSystem.IsWindows()) return [new("","","",false,"unsupported_os",0,0,"Windows probe only")];
        var results=new List<GpuPrimitiveResult>();
        try
        {
            int status=Native.clGetPlatformIDs(0,null,out uint count);
            if(status==-1001) return [new("","","",false,"runtime_unavailable",0,0,"No OpenCL platform")];
            Check(status);
            if(count==0) return [new("","","",false,"runtime_unavailable",0,0,"No OpenCL platform")];
            if(count>64) throw new InvalidOperationException("Platform limit exceeded");
            var platforms=new IntPtr[count]; Check(Native.clGetPlatformIDs(count,platforms,out _));
            foreach(var platform in platforms)
            {
                status=Native.clGetDeviceIDs(platform,4,0,null,out uint devicesCount); // GPU only; CPU OpenCL is not GPU.
                if(status==-1) continue;
                Check(status); if(devicesCount==0) continue;
                if(devicesCount>64) throw new InvalidOperationException("Device limit exceeded");
                var devices=new IntPtr[devicesCount]; Check(Native.clGetDeviceIDs(platform,4,devicesCount,devices,out _));
                foreach(var device in devices)
                {
                    string name=Info(device,0x102B),vendor=Info(device,0x102C),driver=Info(device,0x102D);
                    var caps=new byte[8]; bool fp64=Native.clGetDeviceInfo(device,0x1032,8,caps,out _)==0 && BitConverter.ToUInt64(caps)!=0;
                    if(!fp64) { results.Add(new(name,vendor,driver,false,"fp64_unavailable",0,0,"No advertised double precision capability")); continue; }
                    var watch=Stopwatch.StartNew();
                    try { int checkedValues=Execute(device); results.Add(new(name,vendor,driver,true,"passed",checkedValues,watch.Elapsed.TotalMilliseconds,"Primitive only; full battle unavailable")); }
                    catch(Exception ex) { results.Add(new(name,vendor,driver,true,"failed",0,watch.Elapsed.TotalMilliseconds,ex.Message)); }
                }
            }
            if(results.Count==0) results.Add(new("","","",false,"gpu_unavailable",0,0,"No OpenCL GPU device"));
        }
        catch(Exception ex) when(ex is DllNotFoundException or EntryPointNotFoundException or BadImageFormatException or InvalidOperationException)
        { results.Add(new("","","",false,"runtime_unavailable",0,0,ex.GetType().Name+": "+ex.Message)); }
        return results;
    }
    private static int Execute(IntPtr device)
    {
        double[] values=[-100.5,-2.5,-1.5,-.5,-double.Epsilon,0,.5,1.5,2.5,3.5,
            -Math.BitIncrement(.5),-Math.BitDecrement(.5),Math.BitDecrement(.5),Math.BitIncrement(.5),
            Math.BitDecrement(1),1,Math.BitIncrement(1),Math.BitDecrement(2.5),Math.BitIncrement(2.5),
            30925,31784,196000,1e9+.5,Math.BitDecrement(1e12),1e12];
        var actual=new double[values.Length*6];
        IntPtr context=IntPtr.Zero,queue=IntPtr.Zero,program=IntPtr.Zero,kernel=IntPtr.Zero,a=IntPtr.Zero,b=IntPtr.Zero;
        var input=Marshal.AllocHGlobal(values.Length*sizeof(double));
        var output=Marshal.AllocHGlobal(actual.Length*sizeof(double));
        try
        {
            Marshal.Copy(values,0,input,values.Length);
            context=Native.clCreateContext(IntPtr.Zero,1,[device],IntPtr.Zero,IntPtr.Zero,out int error); Check(error);
            queue=Native.clCreateCommandQueue(context,device,0,out error); Check(error);
            program=Native.clCreateProgramWithSource(context,1,[Kernel],null,out error); Check(error);
            error=Native.clBuildProgram(program,1,[device],"-cl-opt-disable",IntPtr.Zero,IntPtr.Zero);
            if(error!=0)
            {
                var log=new byte[16384]; Native.clGetProgramBuildInfo(program,device,0x1183,(nuint)log.Length,log,out _);
                throw new InvalidOperationException("OpenCL build "+error+": "+Encoding.UTF8.GetString(log).TrimEnd('\0'));
            }
            kernel=Native.clCreateKernel(program,"probe",out error); Check(error);
            a=Native.clCreateBuffer(context,1|32,(nuint)(values.Length*sizeof(double)),input,out error); Check(error);
            b=Native.clCreateBuffer(context,1,(nuint)(actual.Length*sizeof(double)),IntPtr.Zero,out error); Check(error);
            Check(Native.clSetKernelArg(kernel,0,(nuint)IntPtr.Size,ref a)); Check(Native.clSetKernelArg(kernel,1,(nuint)IntPtr.Size,ref b));
            Check(Native.clEnqueueNDRangeKernel(queue,kernel,1,null,[(nuint)values.Length],null,0,IntPtr.Zero,IntPtr.Zero));
            Check(Native.clEnqueueReadBuffer(queue,b,1,0,(nuint)(actual.Length*sizeof(double)),output,0,IntPtr.Zero,IntPtr.Zero));
            Marshal.Copy(output,actual,0,actual.Length);
            for(int i=0;i<values.Length;i++)
            {
                double x=values[i],p=(100000d-30925d)*3.5+x,terms=Math.Floor(p)+Math.Floor(p*.5)+Math.Floor(p);
                double[] expected=[Math.Floor(x),Math.Round(x,MidpointRounding.ToEven),Math.Round(x,MidpointRounding.AwayFromZero),
                    Math.Floor(terms*1.121*1.15*1.1),Math.Floor(Math.Floor(Math.Floor(terms*1.121)*1.15)*1.1),
                    Math.Max(1,Math.Round(p*2.5*1.121*1.15*1.1,MidpointRounding.ToEven))];
                for(int lane=0;lane<6;lane++)
                    if(actual[i*6+lane]!=expected[lane]) throw new InvalidOperationException($"Exact mismatch at value {i}, lane {lane}: {actual[i*6+lane]:R} != {expected[lane]:R}");
            }
            return actual.Length;
        }
        finally
        {
            if(b!=IntPtr.Zero) Native.clReleaseMemObject(b); if(a!=IntPtr.Zero) Native.clReleaseMemObject(a);
            if(kernel!=IntPtr.Zero) Native.clReleaseKernel(kernel); if(program!=IntPtr.Zero) Native.clReleaseProgram(program);
            if(queue!=IntPtr.Zero) Native.clReleaseCommandQueue(queue); if(context!=IntPtr.Zero) Native.clReleaseContext(context);
            Marshal.FreeHGlobal(input); Marshal.FreeHGlobal(output);
        }
    }
    private static string Info(IntPtr device,uint field)
    {
        var value=new byte[4096]; Check(Native.clGetDeviceInfo(device,field,(nuint)value.Length,value,out _));
        return Encoding.UTF8.GetString(value).TrimEnd('\0');
    }
    private static void Check(int code) { if(code!=0) throw new InvalidOperationException("OpenCL error "+code); }
    private static class Native
    {
        private const string Library="OpenCL.dll";
        [DllImport(Library)][DefaultDllImportSearchPaths(DllImportSearchPath.System32)] public static extern int clGetPlatformIDs(uint count,[Out] IntPtr[] ids,out uint actual);
        [DllImport(Library)] public static extern int clGetDeviceIDs(IntPtr platform,ulong type,uint count,[Out] IntPtr[] ids,out uint actual);
        [DllImport(Library)] public static extern int clGetDeviceInfo(IntPtr device,uint field,nuint size,[Out] byte[] value,out nuint actual);
        [DllImport(Library)] public static extern IntPtr clCreateContext(IntPtr props,uint count,IntPtr[] devices,IntPtr callback,IntPtr data,out int error);
        [DllImport(Library)] public static extern IntPtr clCreateCommandQueue(IntPtr context,IntPtr device,ulong props,out int error);
        [DllImport(Library)] public static extern IntPtr clCreateProgramWithSource(IntPtr context,uint count,[MarshalAs(UnmanagedType.LPArray,ArraySubType=UnmanagedType.LPStr)] string[] source,nuint[] lengths,out int error);
        [DllImport(Library,CharSet=CharSet.Ansi)] public static extern int clBuildProgram(IntPtr program,uint count,IntPtr[] devices,string options,IntPtr callback,IntPtr data);
        [DllImport(Library)] public static extern int clGetProgramBuildInfo(IntPtr program,IntPtr device,uint field,nuint size,[Out] byte[] value,out nuint actual);
        [DllImport(Library,CharSet=CharSet.Ansi)] public static extern IntPtr clCreateKernel(IntPtr program,string name,out int error);
        [DllImport(Library)] public static extern IntPtr clCreateBuffer(IntPtr context,ulong flags,nuint size,IntPtr host,out int error);
        [DllImport(Library)] public static extern int clSetKernelArg(IntPtr kernel,uint index,nuint size,ref IntPtr value);
        [DllImport(Library)] public static extern int clEnqueueNDRangeKernel(IntPtr queue,IntPtr kernel,uint dims,nuint[] offset,nuint[] global,nuint[] local,uint count,IntPtr waits,IntPtr evt);
        [DllImport(Library)] public static extern int clEnqueueReadBuffer(IntPtr queue,IntPtr buffer,uint blocking,nuint offset,nuint size,IntPtr host,uint count,IntPtr waits,IntPtr evt);
        [DllImport(Library)] public static extern int clReleaseMemObject(IntPtr obj);
        [DllImport(Library)] public static extern int clReleaseKernel(IntPtr obj);
        [DllImport(Library)] public static extern int clReleaseProgram(IntPtr obj);
        [DllImport(Library)] public static extern int clReleaseCommandQueue(IntPtr obj);
        [DllImport(Library)] public static extern int clReleaseContext(IntPtr obj);
    }
}
