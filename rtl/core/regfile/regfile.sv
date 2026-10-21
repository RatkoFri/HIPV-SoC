///////////////////////////////////////////////////////////////////////
// regfile
//
// Purpose: 32 x 32-bit register file. Two combinational read ports
//          (A1/RD1, A2/RD2), one synchronous write port (A3/WD3/WE3)
//          driven by the Writeback stage. x0 always reads as zero.
//          Read ports bypass a same-cycle write (write-first), so an
//          instruction in Decode sees the value being written back in
//          the same cycle without an extra forwarding path.
//          The register array is not reset; software must write a
//          register before reading it.
// Author:  Ratko Pilipovic
// Date:    10 August 2026
///////////////////////////////////////////////////////////////////////

module regfile (input  logic        clk,
                input  logic        WE3,
                input  logic [4:0]  A1, A2, A3,
                input  logic [31:0] WD3,
                output logic [31:0] RD1, RD2);

  // 0. Storage: array of 32 registers, 32 bits each (RF[31:0])
  //    No reset; software writes a register before reading it.

  // 1. Write port (always_ff, rising edge of clk)
  //    - write WD3 to RF[A3] when WE3 and A3 is not x0

  // 2. Read ports (combinational assign), for RD1 (A1) and RD2 (A2):
  //    - address x0                 -> 32'b0
  //    - same-cycle write (WE3 and address == A3) -> WD3 (write-first bypass)
  //    - otherwise                  -> RF[address]

endmodule
