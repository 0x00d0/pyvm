from pyVmomi import vim, vmodl
from pyVim.connect import SmartConnect, Disconnect
import ssl
import logging
import traceback


def connect_vc(host, user, pwd, port=443,):
    """
    连接Vcenter
    :return:
    """

    context = ssl.SSLContext(ssl.PROTOCOL_TLSv1)
    context.verify_mode = ssl.CERT_NONE
    service_instance = SmartConnect(host=host, user=user, pwd=pwd, port=port, sslContext=context)
    return service_instance


def get_obj(content, vimtype, name):
    """
    :param content:
    :param vimtype: [vim.Datacenter]，[vim.Folder]，[vim.Datastore]，[vim.ClusterComputeResource]，[vim.ResourcePool]，[vim.StoragePod]，[vim.HostSystem]
    :param name:
    :return:
    """

    obj = None
    container = content.viewManager.CreateContainerView(content.rootFolder, vimtype, True)
    for vm in container.view:
        if name:
            if vm.name == name:
                obj = vm
                break
        else:
            obj = vm
            break
    return obj


def wait_for_task(task):
    """
    返回任务执行状态及结果
    :param task:
    :return:
    """

    task_done = False
    while not task_done:
        if task.info.state == "success":
            print("task.info.result", task.info.result)
            return task.info.result
        if task.info.state == "error":
            # task_done = True
            print('task.info.error.msg', task.info.error.msg)
            return task.info.error.msg


def poweronvm(content, vmname):
    """
    打开指定虚拟机电源
    :param content:
    :param vmname: 虚拟机名称  type:str
    :return:
    """

    # vm = content.searchIndex.FindChild(content.rootFolder.childEntity[0].vmFolder,vmname)
    vm = get_obj(content, [vim.VirtualMachine], vmname)
    if vm.summary.runtime.powerState == "poweredOn":
        print("当前虚拟机电源状态poweredOn,无法执行poweredOn操作")
        return
    task = vm.PowerOnVM_Task()
    wait_for_task(task)


def poweroffvm(content, vmname):
    """
    关闭指定虚拟机电源
    :param content:
    :param vmname:
    :return:
    """
    # vm = content.searchIndex.FindChild(content.rootFolder.childEntity[0].vmFolder, vmname)
    vm = get_obj(content, [vim.VirtualMachine], vmname)
    if vm.summary.runtime.powerState != "poweredOn":
        logger.info("当前虚拟机电源状态不是poweredOn,无法执行poweredOff操作")
        return
    task = vm.PowerOffVM_Task()
    wait_for_task(task)


def resetvm(content, vmname):
    """
    重启指定虚拟机
    :param content:
    :param vmname:
    :return:
    """

    vm = content.searchIndex.FindChild(content.rootFolder.childEntity[0].vmFolder, vmname)
    if vm.summary.runtime.powerState == "poweredOn":
        task = vm.ResetVM_Task()
        wait_for_task(task)


def get_datacenter_list(content):
    """
    获取VCenter下所有的数据中心
    :param content:
    :return:
    """

    datacenter = content.viewManager.CreateContainerView(content.rootFolder, [vim.Datacenter], True)
    datacenter_list = [{"dc_moid": dc._moId, "dc_name": dc.name} for dc in datacenter.view]
    return datacenter_list


def get_datacenter_hosts(content, datacentername):
    """
    获取指定数据中心下所有主机
    :param content:
    :return:
    """

    datacenter = get_obj(content, [vim.Datacenter], datacentername)
    hosts_list = []
    container = content.viewManager.CreateContainerView(datacenter.hostFolder, [vim.HostSystem], True)
    for host in container.view:
        hosts_list.append(host.name)

    return hosts_list


def get_host_info(content, hostname):
    """
    获取指定esxi主机信息
    :param content:
    :param hostname: esxi名称 是 IP地址
    :return:
    """

    host = get_obj(content, [vim.HostSystem], hostname)
    hostinfo = {
        'vendor': host.summary.hardware.vendor,  # 厂商
        'model': host.summary.hardware.model,  # 服务器型号
        'uuid': host.summary.hardware.uuid,  # uuid
        'cpuModel': host.summary.hardware.cpuModel,  # CPU型号
        'cpuMhz': host.summary.hardware.cpuMhz,  # CPU频率
        'numCpuPkgs': host.summary.hardware.numCpuPkgs,  # 物理插槽
        'numCpuCores': host.summary.hardware.numCpuCores,  # CPU核心
        'numCpuThreads': host.summary.hardware.numCpuThreads,  # 逻辑CPU个数
        'memorySize': host.summary.hardware.memorySize,  # 总内存
        'uptime': host.summary.quickStats.uptime,  # 运行时长
        'fullName': host.summary.config.product.fullName,  # fullName
        'port': host.summary.config.port,  # 管理端口
        'vm_num': len(host.vm),  # 虚拟机数量
        'datastore_num': len(host.datastore),
    }
    return hostinfo


def get_host_vm(content, hostname):
    """
    获取指定esxi主机下虚拟机信息
    :param content:
    :return:
    """

    host = get_obj(content, [vim.HostSystem], hostname)
    vminfo = {}
    for vm in host.vm:
        vminfo[vm.name] = {
            "template": vm.summary.config.template,
            "vmPathName": vm.summary.config.vmPathName,
            "memorySizeMB": vm.summary.config.memorySizeMB,
            "numCpu": vm.summary.config.numCpu,
            "uuid": vm.summary.config.uuid,
            "instanceUuid": vm.summary.config.instanceUuid,
            "guestId": vm.summary.config.guestId,
            "guestFullName": vm.summary.config.guestFullName,
            "powerState": vm.summary.runtime.powerState,
            "bootTime": str(vm.summary.runtime.bootTime),
            "hostName": vm.summary.guest.hostName,
            "ipAddress": vm.summary.guest.ipAddress,
            "VirtualDisk": str([da.capacityInKB for da in vm.config.hardware.device if
                                isinstance(da, vim.vm.device.VirtualDisk)]).rstrip("]").lstrip("["),
            "VirtualCdrom": str([cdrom.deviceInfo.summary for cdrom in vm.config.hardware.device if
                                 isinstance(cdrom, vim.vm.device.VirtualCdrom)]).rstrip("]").lstrip("["),
            "datastore_name": str([da.backing.datastore.name for da in vm.config.hardware.device if
                                   isinstance(da, vim.vm.device.VirtualDisk)]).rstrip("]").lstrip("["),
        }
    return vminfo


def get_all_hosts_info(content):
    """
    获取VCenter下所有的主机信息
    :param content:
    :return:
    """

    containerView = content.viewManager.CreateContainerView(content.rootFolder, [vim.HostSystem], True)
    hosts = {}
    for host in containerView.view:
        hosts[host.name] = {
            'vendor': host.summary.hardware.vendor,  # 厂商
            'model': host.summary.hardware.model,  # 服务器型号
            'uuid': host.summary.hardware.uuid,  # uuid
            'cpuModel': host.summary.hardware.cpuModel,  # CPU型号
            'cpuMhz': host.summary.hardware.cpuMhz,  # CPU频率
            'cpuusage': '%.1f%%' % (host.summary.quickStats.overallCpuUsage / (host.summary.hardware.numCpuPkgs * host.summary.hardware.numCpuCores * host.summary.hardware.cpuMhz) * 100),  # 处理器使用率
            'numCpuPkgs': host.summary.hardware.numCpuPkgs,  # 物理插槽
            'numCpuCores': host.summary.hardware.numCpuCores,  # CPU核心
            'numCpuThreads': host.summary.hardware.numCpuThreads,  # 逻辑CPU个数
            'memorysize': '%.1f GB' % (((host.summary.hardware.memorySize / 1024 / 1024) - host.summary.quickStats.overallMemoryUsage) / 1024),  # 可用内存(GB)
            'memorytotal': str(host.summary.hardware.memorySize / 1024 / 1024 /1024).split('.')[0] + "GB",  # 总内存
            'uptime': host.summary.quickStats.uptime,  # 运行时长
            'fullName': host.summary.config.product.fullName,  # fullName
            'port': host.summary.config.port,  # 管理端口
            'powerstate': host.runtime.powerState,
            'boottime': str(host.runtime.bootTime),
            'overallmemory': '%.1f%%' % ((host.summary.quickStats.overallMemoryUsage / (host.summary.hardware.memorySize / 1024 / 1024)) * 100),  # 内存使用率
            'vm_num': len(host.vm),  # 虚拟机数量
            'datastore_num': len(host.datastore),
        }

    return hosts


def get_all_resource_pool(content):
    """
    获取VC下所有资源池
    :param content:
    :return:
    """
    resource_pool = content.viewManager.CreateContainerView(content.rootFolder, [vim.ResourcePool], True)
    pool_list = []
    for pool in resource_pool.view:
        pool_list.append({"pool_name": pool.name, "pool_id": pool._moId})

    return pool_list


def get_host_resource_pool(content, hostname):
    """
    获取指定主机上的资源池
    :param content:
    :param hostname:
    :return:
    """
    host = get_obj(content, [vim.ComputeResource], hostname)
    pool_list = []
    if host:
        for pool in host.resourcePool.resourcePool:
            pool_list.append({"pool_name": pool.name, "pool_id": pool._moId})
        return pool_list
    else:
        return


def get_all_vmfolder(content):
    """

    :param content:
    :return:
    """
    vm_folder = content.viewManager.CreateContainerView(content.rootFolder, [vim.Folder], True)
    vmfolder_list = []
    for vmfolder in vm_folder.view:
        if vmfolder.name not in ['host', 'datastore', 'network']:
            vmfolder_list.append({"vmfolder_name": vmfolder.name, "vmfolder_id": vmfolder._moId})

    return vmfolder_list


def get_all_vms(content):
    """
    获取所有虚拟机
    :param content:
    :return:
    """

    datacenter = content.viewManager.CreateContainerView(content.rootFolder, [vim.Datacenter], True).view
    vms_list = []
    for dc in datacenter:
        vms = content.viewManager.CreateContainerView(dc.vmFolder, [vim.VirtualMachine], True).view
        for i in vms:
            summary = i.summary
            runtime = summary.runtime
            hc = runtime.host.parent
            # if summary.config.template == False:
            vms_list.append({'moId': i._moId, 'name': i.name, 'hc_moId': hc._moId, 'hc_name': hc.name,
                             'hostip': summary.guest.ipAddress, 'dc_moId': dc._moId, 'dc_name': dc.name,
                             'vm_os': summary.config.guestFullName})

    return vms_list


def clone_vm(content, template, vm_name, datacenter_name, vm_folder, datastore_name, resource_pool, power_on, numcpu,
             mensize, ipaddr, subnetmask, gateway, dnsdomain, newvmhostname, dnsServerList):
    '''
    从template/VM 克隆一个虚拟机，
    :param content:
    :param template:
    :param vm_name:
    :param service_instance:
    :param datacenter_name:
    :param vm_folder:
    :param datastore_name:
    :param cluster_name:
    :param resource_pool:
    :param power_on:
    :param datastorecluster_name:
    :return:
    '''
    # 获取指定的datacenter，如果没有就第一个
    datacenter = get_obj(content, [vim.Datacenter], datacenter_name)
    if vm_folder:
        destfolder = get_obj(content, [vim.Folder], vm_folder)
    else:
        destfolder = datacenter.vmFolder
    template = get_obj(content, [vim.VirtualMachine], template)
    if datastore_name:
        datastore = get_obj(content, [vim.Datastore], datastore_name)
    else:
        datastore = get_obj(content, [vim.Datastore], template.datastore[0].info.name)
    if resource_pool:
        resource_pool = get_obj(content, [vim.ResourcePool], resource_pool)

    print('设置%s CPU、内存' % (vm_name))
    specconfig = vim.vm.ConfigSpec(numCPUs=int(numcpu), memoryMB=int(mensize))
    print("设置Network ")
    adaptermap = vim.vm.customization.AdapterMapping()
    # HDCP
    # adaptermap.adapter = vim.vm.customization.IPSettings(ip=vim.vm.customization.DhcpIpGenerator(), dnsDomain='localhost')
    adaptermap.adapter = vim.vm.customization.IPSettings(ip=vim.vm.customization.FixedIp(ipAddress=ipaddr),
                                                         subnetMask=subnetmask, gateway=gateway)
    print("设置DNS")
    # 动态获取DNS
    #globalip = vim.vm.customization.GlobalIPSettings()
    # 静态设置
    globalip = vim.vm.customization.GlobalIPSettings(dnsServerList=dnsServerList)
    print("设置 hostname")
    ident = vim.vm.customization.LinuxPrep(domain=dnsdomain,
                                           hostName=vim.vm.customization.FixedName(name=newvmhostname))

    customspec = vim.vm.customization.Specification(nicSettingMap=[adaptermap], globalIPSettings=globalip,
                                                    identity=ident)
    # config = get_vmconfig(content,1,1024,template,40)
    relospec = vim.vm.RelocateSpec()
    relospec.datastore = datastore
    relospec.pool = resource_pool
    clonespec = vim.vm.CloneSpec(powerOn=power_on, template=False, location=relospec, customization=customspec, config=specconfig)

    print("cloning VM...")
    # print(template.parent)
    task = template.Clone(folder=destfolder, name=vm_name, spec=clonespec)
    wait_for_task(task)


    # vm = get_obj(content, [vim.VirtualMachine], vm_name)
    # vmtask = vm.ReconfigVM_Task(spec=spec)
    # wait_for_task(vmtask)


if __name__ == '__main__':
    service_instance = connect_vc(host="", user="", pwd="")
    content = service_instance.RetrieveContent()
    clone_vm(content=content, template='CentOS7-templates', vm_name='clone_vm_test3',
             datacenter_name='DataCenter', vm_folder='', datastore_name='Datastore',
             resource_pool='Resources', power_on=False, numcpu=2, mensize=4096, ipaddr="192.168.1.16",
             subnetmask="255.255.255.0", gateway="192.168.1.1", dnsdomain="localhost", newvmhostname="clonevmtest",
             dnsServerList=['223.5.5.5', '114.114.114.114'])
    Disconnect(service_instance)


