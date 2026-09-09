/* G5 dropped output-codec7 acceptance and the corresponding log name. */
#define HD_STATUS_COMPARE 0xffffffc010f3b56cUL
#define HD_STATUS_ACCEPT  0xffffffc010f3b66cUL
#define HD_STATUS_NAME    0xffffffc010f3b62cUL
static atomic_t hd_status_hits = ATOMIC_INIT(0);
static const char hd_name[] = "dts-hd";
static const char unknown_name[] = "unknown";
static int status_pre(struct kprobe *p, struct pt_regs *r)
{
    unsigned long output = r->regs[19];
    (void)p;
    if (enable && r->regs[6] == 7 && output &&
        READ_ONCE(*(u32 *)(output + 0x2c)) == 3 &&
        READ_ONCE(*(u32 *)DTS_ADEC1_CODEC) == 51 &&
        READ_ONCE(*(u8 *)DTS_ADEC1_STARTED) == 1) {
        /* Preserve codec7 and follow the existing supported-format branch.
         * _set_type selects non-PCM hardware transport for nonzero codec.
         * No source metadata or payload is re-labelled as another codec. */
        atomic_inc(&hd_status_hits);
        r->pc = HD_STATUS_ACCEPT;
        return 1;
    }
    return 0;
}
NOKPROBE_SYMBOL(status_pre);
static int status_name_pre(struct kprobe *p, struct pt_regs *r)
{
    (void)p;
    /* Original table contains only entries0..5. Never dereference later text
     * as a pointer, even if a different unsupported format is reported. */
    if (r->regs[4] > 5) {
        r->regs[7] = (unsigned long)(r->regs[4] == 7 ? hd_name : unknown_name);
        r->pc = HD_STATUS_NAME + 4;
        return 1;
    }
    return 0;
}
NOKPROBE_SYMBOL(status_name_pre);
static struct kprobe hd_status_probe = {
    .addr = (void *)HD_STATUS_COMPARE, .pre_handler = status_pre,
};
static struct kprobe hd_name_probe = {
    .addr = (void *)HD_STATUS_NAME, .pre_handler = status_name_pre,
};
static struct kprobe *hd_probes[] = {&hd_name_probe, &hd_status_probe};
