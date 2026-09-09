#include <linux/module.h>
#include <linux/init.h>
#include <linux/cpu.h>
#include <linux/errno.h>
#include <linux/string.h>
#include <linux/utsname.h>

/* Installed OLED77G5RLA 33.30.80 ONLY; verified against live memory. */
#define GATE_ADDRESS 0xffffffc010f79130UL
#define PATCH_ADDRESS 0xffffffc01132f520UL
#define ORIGINAL 0x52800000U
#define ENABLED 0x52800020U
static bool enable;
module_param(enable, bool, 0400);
MODULE_PARM_DESC(enable, "Apply temporary DTS gate change (default: probe only)");
static bool changed;
typedef int (*patch_fn)(void **, u32 *, int);
static int set_gate(u32 expected, u32 replacement)
{
    void *addr = (void *)GATE_ADDRESS;
    int result;
    cpus_read_lock();
    if (READ_ONCE(*(u32 *)addr) != expected ||
        READ_ONCE(*((u32 *)addr + 1)) != 0xd65f03c0U) {
        cpus_read_unlock();
        return -EINVAL;
    }
    result = ((patch_fn)PATCH_ADDRESS)(&addr, &replacement, 1);
    cpus_read_unlock();
    return result;
}
static int __init dts_gate_init(void)
{
    int result;
    if (strcmp(init_utsname()->release, "5.4.268-329.ptl4tv.5"))
        return -EINVAL;
    if (READ_ONCE(*(u32 *)GATE_ADDRESS) != ORIGINAL ||
        READ_ONCE(*(u32 *)(GATE_ADDRESS + 4)) != 0xd65f03c0U ||
        READ_ONCE(*(u32 *)PATCH_ADDRESS) != 0xa9bd7bfdU)
        return -EINVAL;
    pr_info("dts_gate: verified original gate; enable=%d\n", enable);
    if (!enable) return 0;
    result = set_gate(ORIGINAL, ENABLED);
    if (result) return result;
    changed = true;
    pr_info("dts_gate: temporary gate enabled\n");
    return 0;
}
static void __exit dts_gate_exit(void)
{
    if (changed) {
        int result = set_gate(ENABLED, ORIGINAL);
        pr_info("dts_gate: restore result=%d\n", result);
    } else pr_info("dts_gate: probe unloaded; no changes\n");
}
module_init(dts_gate_init);
module_exit(dts_gate_exit);
MODULE_LICENSE("GPL");
MODULE_DESCRIPTION("Temporary, version-locked LG DTS gate experiment");
