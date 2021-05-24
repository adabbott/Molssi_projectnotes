// standard C++ headers
//#include <cmath>
#include <iostream>
//#include <fstream>
//#include <sstream>
//#include <iomanip>
//#include <vector>
//#include <chrono>

// Libint 
//#include <libint2.hpp>
#include "libint2.hpp"
//#if !LIBINT2_CONSTEXPR_STATICS
//#  include <libint2/statics_definition.h>
//#endif

int main() {
  //libint2::initialize();
  //libint2::finalize();
  std::cout << "Hello";
  return 0;
}


// -I/home/adabbott/Git/dummy_libint/libint-2.7.0-beta.3/include -I/home/adabbott/Git/dummy_libint/libint-2.7.0-beta.3/include/libint2
// -L/home/adabbott/Git/dummy_libint/libint-2.7.0-beta.3/lib
// clang++ -I/home/adabbott/Git/dummy_libint/libint-2.7.0-beta.3/include -I/home/adabbott/Git/dummy_libint/libint-2.7.0-beta.3/include/libint2 -L/home/adabbott/Git/dummy_libint/libint-2.7.0-beta.3/lib -I/home/adabbott/anaconda3/envs/psijax/include/eigen3 comon.cc

// g++ -std=c++11 -I/usr/local/include -I/usr/local/include/libint2 -L/usr/local/lib/ -I/usr/include/eigen3 comon.cc -o comon.o

// g++ -std=c++11 -I/usr/local/include -L/usr/local/lib/ -I/usr/include/eigen3 comon.cc -o comon.o

// CPPFLAGS := -I../include -I../include/libint2 -Ieri -Ihartree-fock -DSRCDATADIR=\"$(SRCDIR)/lib/basis\" $(CPPFLAGS)
// COMPUTE_LIB = -L../lib -lint2


// NEW CONDA ENV
// gcc -std=c++11 -I/home/adabbott/anaconda3/envs/libint/include/eigen3 -I/home/adabbott/anaconda3/envs/libint/include/libint2 -I/home/adabbott/anaconda3/envs/libint/include/ -L/home/adabbott/anaconda3/envs/libint/lib/ comon.cpp -o comon.o