int main(void) {
  unsigned x = 0;
  while (1) {
    if (x < 10) x++;
    __ESBMC_assert(x <= 10, "bounded");
  }
}
