#include <assert.h>
#include "../policy.h"
int main(void) {
 unsigned int i,o,c,open,start;
 for(i=0;i<3;i++) for(o=0;o<4096;o++) for(c=0;c<67;c++)
 for(open=0;open<2;open++) for(start=0;start<2;start++) {
  int want=i==1 && o==32 && c==48 && open && start;
  assert(dts_core_route_matches(i,o,c,open,start)==want);
 }
 return 0;
}
