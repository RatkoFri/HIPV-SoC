///////////////////////////////////////////////////////////////////////
// hipv_soc_pkg
//
// Purpose: SoC-level constants for HIPV: crossbar master and slave
//          indices, the address map, and the arbitration policy
//          encoding. Imported by the interconnect and by the SoC top
//          level so both agree on the map.
// Author:  Ratko Pilipovic
// Date:    12 August 2026
///////////////////////////////////////////////////////////////////////

// not every unit uses every constant; that is fine for a shared package
/* verilator lint_off UNUSEDPARAM */
package hipv_soc_pkg;

  // crossbar masters
  // MASTER_D is index 0 so that fixed-priority arbitration (lowest index
  // wins) favours data accesses over instruction fetch.
  localparam int unsigned NUM_MASTERS = 2;
  localparam int unsigned MASTER_D    = 0;  // load/store unit
  localparam int unsigned MASTER_I    = 1;  // instruction fetch unit

  // crossbar slaves
  localparam int unsigned NUM_SLAVES = 5;
  localparam int unsigned SLAVE_IMEM  = 0;
  localparam int unsigned SLAVE_DMEM  = 1;
  localparam int unsigned SLAVE_UART  = 2;
  localparam int unsigned SLAVE_TIMER = 3;
  localparam int unsigned SLAVE_GPIO  = 4;

  // address map: BASE is the first address, SIZE the region size in
  // bytes. Regions must be power-of-two sized and naturally aligned so
  // the decoder can compare the upper address bits only.
  localparam logic [31:0] IMEM_BASE  = 32'h0000_0000;
  localparam logic [31:0] IMEM_SIZE  = 32'h0001_0000;  // 64 KiB
  localparam logic [31:0] DMEM_BASE  = 32'h1000_0000;
  localparam logic [31:0] DMEM_SIZE  = 32'h0001_0000;  // 64 KiB
  localparam logic [31:0] UART_BASE  = 32'h2000_0000;
  localparam logic [31:0] UART_SIZE  = 32'h0000_1000;  // 4 KiB
  localparam logic [31:0] TIMER_BASE = 32'h2000_1000;
  localparam logic [31:0] TIMER_SIZE = 32'h0000_1000;  // 4 KiB
  localparam logic [31:0] GPIO_BASE  = 32'h2000_2000;
  localparam logic [31:0] GPIO_SIZE  = 32'h0000_1000;  // 4 KiB

  // arbitration policy (ARB_POLICY parameter of obi_arbiter)
  localparam int unsigned ARB_FIXED       = 0;  // lowest master index wins
  localparam int unsigned ARB_ROUND_ROBIN = 1;  // rotating priority

endpackage
/* verilator lint_on UNUSEDPARAM */
