// SPDX-License-Identifier: GPL-2.0
/* Experimental OLED77G5RLA 33.30.80 ONLY. Exact target only; see docs/validation.md. */
#include <linux/module.h>
#include <linux/kprobes.h>
#include <linux/utsname.h>
#include <linux/string.h>
#include <linux/jiffies.h>
#include "policy.h"
#include "target.h"
#include "break_bridge.h"

static bool selftest_only = true;
module_param(selftest_only, bool, 0400);
MODULE_PARM_DESC(selftest_only, "Only test BRK dispatch locally; default true");
static bool route_registered;

static bool enable;
module_param(enable, bool, 0400);
MODULE_PARM_DESC(enable, "Enable scoped eARC bypass override; default observes only");
static unsigned int window_seconds = 30;
module_param(window_seconds, uint, 0400);
static unsigned long expires;
static atomic_t matches = ATOMIC_INIT(0);
static atomic_t overrides = ATOMIC_INIT(0);

static int route_pre(struct kprobe *p, struct pt_regs *regs)
{
    unsigned int codec, open, started, mask;
    unsigned long out = regs->regs[1];
    (void)p;
    if ((unsigned int)regs->regs[0] != 1 || !out) return 0;
    /* _set_output already requires this output-descriptor pointer to be valid. */
    mask = READ_ONCE(*(u32 *)(out + 0x14));
    if (mask != 0x20) return 0; /* eARC only; never speakers/optical/headphones */
    codec = READ_ONCE(*(u32 *)DTS_ADEC1_CODEC);
    open = READ_ONCE(*(u8 *)DTS_ADEC1_OPEN);
    started = READ_ONCE(*(u8 *)DTS_ADEC1_STARTED);
    if (!dts_core_route_matches(regs->regs[0], mask, codec, open, started))
        return 0;
    if (atomic_inc_return(&matches) <= 5)
        pr_info("dts_core_route: core eARC decision codec=%lu bypass=%lu\n",
                regs->regs[2], regs->regs[3]);
    if (!enable || (window_seconds && time_after_eq(jiffies, expires))) return 0;
    /* bypass=true selects compressed port 0x100, not a PCM interpretation.
     * output_set_format is a logging-only stub on this exact build. Actual
     * transport format must come from the DTS HDMI bypass metadata. Keep
     * codec=0 as neutral routing argument; no transcoder is selected.
     */
    regs->regs[2] = 0;
    regs->regs[3] = 1;
    atomic_inc(&overrides);
    return 0;
}
NOKPROBE_SYMBOL(route_pre);
static struct kprobe route_probe = {
    .addr = (kprobe_opcode_t *)DTS_SET_OUTPUT,
    .pre_handler = route_pre,
};
static int __init core_init(void)
{
    unsigned int i;
    int ret;
    BUILD_BUG_ON(offsetof(struct kprobe, addr) != 0x28);
    BUILD_BUG_ON(offsetof(struct kprobe, pre_handler) != 0x40);
    BUILD_BUG_ON(offsetof(struct kprobe, flags) != 0x80);
    if (strcmp(init_utsname()->release, "5.4.268-329.ptl4tv.5")) return -EINVAL;
    if (window_seconds > 120) return -EINVAL;
    for (i = 0; i < ARRAY_SIZE(target_checks); i++)
        if (memcmp((void *)target_checks[i].addr, target_checks[i].bytes,
                   sizeof(target_checks[i].bytes))) {
            pr_err("dts_core_route: target fingerprint mismatch %u\n", i);
            return -EINVAL;
        }
    ret = bridge_install();
    if (ret) return ret;
    ret = bridge_selftest();
    if (ret) { bridge_remove(); return ret; }
    if (selftest_only) return 0;
    expires = jiffies + window_seconds * HZ;
    ret = register_kprobe(&route_probe);
    if (ret) { bridge_remove(); return ret; }
    route_registered = true;
    if (!ret) pr_info("dts_core_route: %s, window=%us (0=supervised session)\n",
                      enable ? "enabled" : "observe only", window_seconds);
    return ret;
}
static void __exit core_exit(void)
{
    if (route_registered) unregister_kprobe(&route_probe);
    bridge_remove();
    pr_info("dts_core_route: unloaded matches=%d overrides=%d missed=%lu\n",
            atomic_read(&matches), atomic_read(&overrides), route_probe.nmissed);
    /* Unregistering restores instruction text, not the resulting audio graph.
     * The controller must reset the eARC control and HDMI session afterward. */
}
module_init(core_init);
module_exit(core_exit);
MODULE_LICENSE("GPL");
MODULE_DESCRIPTION("Version-locked, temporary DTS core eARC bypass candidate");
