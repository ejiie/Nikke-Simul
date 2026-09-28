"""Read-only Windows telemetry. No settings, process command lines, or user files."""
import ctypes as c
from ctypes import wintypes as w
import os,time,uuid,shutil
from pathlib import Path

k=c.WinDLL('kernel32',use_last_error=True);p=c.WinDLL('psapi',use_last_error=True)
u=c.WinDLL('user32',use_last_error=True);power=c.WinDLL('powrprof',use_last_error=True)
k.OpenProcess.argtypes=[w.DWORD,w.BOOL,w.DWORD];k.OpenProcess.restype=w.HANDLE
k.CloseHandle.argtypes=[w.HANDLE]
k.GetProcessTimes.argtypes=[w.HANDLE,c.c_void_p,c.c_void_p,c.c_void_p,c.c_void_p]
k.QueryFullProcessImageNameW.argtypes=[w.HANDLE,w.DWORD,w.LPWSTR,c.POINTER(w.DWORD)]
p.GetProcessMemoryInfo.argtypes=[w.HANDLE,c.c_void_p,w.DWORD]
k.LocalFree.argtypes=[c.c_void_p];k.LocalFree.restype=c.c_void_p
u.OpenInputDesktop.argtypes=[w.DWORD,w.BOOL,w.DWORD];u.OpenInputDesktop.restype=w.HANDLE
u.GetUserObjectInformationW.argtypes=[w.HANDLE,c.c_int,c.c_void_p,w.DWORD,c.POINTER(w.DWORD)]
u.CloseDesktop.argtypes=[w.HANDLE]
class Battery(c.Structure):
    _fields_=[('ACLineStatus',c.c_ubyte),('BatteryFlag',c.c_ubyte),('BatteryLifePercent',c.c_ubyte),('SystemStatusFlag',c.c_ubyte),('BatteryLifeTime',w.DWORD),('BatteryFullLifeTime',w.DWORD)]
class Memory(c.Structure):
    _fields_=[('length',w.DWORD),('load',w.DWORD)]+[(name,c.c_ulonglong) for name in ('totalPhysical','availablePhysical','totalPageFile','availablePageFile','totalVirtual','availableVirtual','availableExtendedVirtual')]
class ProcessMemory(c.Structure):
    _fields_=[('cb',w.DWORD),('pageFaults',w.DWORD)]+[(name,c.c_size_t) for name in ('peakWorkingSet','workingSet','quotaPeakPagedPool','quotaPagedPool','quotaPeakNonPagedPool','quotaNonPagedPool','pageFile','peakPageFile','privateBytes')]
def environment():
    b=Battery();assert k.GetSystemPowerStatus(c.byref(b))
    m=Memory();m.length=c.sizeof(m);assert k.GlobalMemoryStatusEx(c.byref(m))
    ptr=c.c_void_p();assert power.PowerGetActiveScheme(None,c.byref(ptr))==0
    try:scheme=str(uuid.UUID(bytes_le=c.string_at(ptr,16)))
    finally:k.LocalFree(ptr)
    desktop=u.OpenInputDesktop(0,False,1);name=None
    if desktop:
        try:
            buf=c.create_unicode_buffer(256);needed=w.DWORD()
            if u.GetUserObjectInformationW(desktop,2,buf,c.sizeof(buf),c.byref(needed)):name=buf.value
        finally:u.CloseDesktop(desktop)
    return dict(ac=b.ACLineStatus,batteryPercent=None if b.BatteryLifePercent==255 else b.BatteryLifePercent,batterySaver=b.SystemStatusFlag,powerScheme=scheme,desktop=name,memoryLoadPercent=m.load,availablePhysical=m.availablePhysical,totalPhysical=m.totalPhysical)
class Sampler:
    def __init__(self):self.previous={};self.at=None;self.system=None
    def sample(self,own_pid=None,storage=None):
        now=time.monotonic();elapsed=None if self.at is None else now-self.at;self.at=now
        arr=(w.DWORD*8192)();size=w.DWORD();assert p.EnumProcesses(arr,c.sizeof(arr),c.byref(size))
        processes=[];current={};unreadable=0
        for pid in arr[:size.value//c.sizeof(w.DWORD)]:
            handle=k.OpenProcess(0x1000,False,pid)
            if not handle:unreadable+=1;continue
            try:
                buf=c.create_unicode_buffer(4096);length=w.DWORD(len(buf));times=[c.c_ulonglong() for _ in range(4)]
                if not k.QueryFullProcessImageNameW(handle,0,buf,c.byref(length)):unreadable+=1;continue
                if not k.GetProcessTimes(handle,*[c.byref(v) for v in times]):unreadable+=1;continue
                cpu=(times[2].value+times[3].value)/1e7;key=(pid,times[0].value);current[key]=cpu
                delta=None if key not in self.previous or not elapsed else max(0,cpu-self.previous[key])/elapsed
                row=dict(pid=pid,name=Path(buf.value).name,cpuSeconds=cpu,cpuCores=delta)
                if pid==own_pid:
                    mem=ProcessMemory();mem.cb=c.sizeof(mem)
                    if p.GetProcessMemoryInfo(handle,c.byref(mem),c.sizeof(mem)):
                        row.update(workingSet=mem.workingSet,privateBytes=mem.privateBytes,peakWorkingSet=mem.peakWorkingSet)
                processes.append(row)
            finally:k.CloseHandle(handle)
        self.previous=current
        times=[c.c_ulonglong() for _ in range(3)];assert k.GetSystemTimes(*[c.byref(v) for v in times])
        vals=[v.value for v in times];cpuPercent=None
        if self.system:
            idle,kernel,user=[a-b for a,b in zip(vals,self.system)];total=kernel+user
            cpuPercent=100*(total-idle)/total if total else None
        self.system=vals
        info=environment();info.update(epoch=time.time(),intervalSeconds=elapsed,systemCpuPercent=cpuPercent,logicalProcessors=os.cpu_count(),processes=processes,unreadableProcesses=unreadable)
        if storage:
            volume=Path(storage)
            while not volume.exists():volume=volume.parent
            info['diskFreeBytes']=shutil.disk_usage(volume).free
            info['storageBytes']=sum(f.stat().st_size for f in Path(storage).rglob('*') if f.is_file())
        return info
if __name__=='__main__':
    import json
    s=Sampler();s.sample(os.getpid());time.sleep(1);print(json.dumps(s.sample(os.getpid()),ensure_ascii=False))
