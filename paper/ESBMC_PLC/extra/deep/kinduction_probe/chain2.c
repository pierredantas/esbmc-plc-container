_Bool nondet_bool(void);
int main(void) {
  _Bool a1 = 0, a2 = 0, b1 = 0, b2 = 0;
  while (1) {
    _Bool in = nondet_bool();
    a2 = a1; b2 = b1;
    a1 = in; b1 = in;
    __ESBMC_assert(a2 == b2, "outputs agree");
  }
}
