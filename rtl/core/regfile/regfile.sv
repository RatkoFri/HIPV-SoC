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

  logic [31:0] RF[31:0];

  // synchronous write port (writes to x0 are ignored)
  always_ff @(posedge clk)
    if (WE3 & (A3 != 5'b0)) RF[A3] <= WD3;

  // combinational read ports with write-first bypass
  assign RD1 = (A1 == 5'b0) ? 32'b0 : (WE3 & (A1 == A3)) ? WD3 : RF[A1];
  assign RD2 = (A2 == 5'b0) ? 32'b0 : (WE3 & (A2 == A3)) ? WD3 : RF[A2];

endmodule
