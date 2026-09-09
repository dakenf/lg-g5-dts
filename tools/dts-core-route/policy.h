#ifndef DTS_CORE_POLICY_H
#define DTS_CORE_POLICY_H
/* Values proven in the installed driver's disassembly. */
static inline int dts_core_route_matches(unsigned int adec_index,
        unsigned int output_mask, unsigned int public_codec,
        unsigned int adec_open, unsigned int adec_started)
{
    return adec_index == 1 && output_mask == 0x20 && public_codec == 48 &&
           adec_open == 1 && adec_started == 1;
}
#endif
