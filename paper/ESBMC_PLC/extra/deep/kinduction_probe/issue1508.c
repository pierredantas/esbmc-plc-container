#include <string.h>
void reach_error(void) { __ESBMC_assert(0, "reach_error"); }
float a;
int main(void) {
  for (;;) {
    memset(&a, 0, sizeof(a));
    reach_error();
    for (;;)
      ;
  }
}
