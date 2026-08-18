///////////////////////////////////////////////////////////////////////
// obi_ram
//
// Purpose: Unified SoC memory: ONE true dual-port RAM behind TWO
//          independent OBI slave ports. In the SoC, port A serves the
//          IMEM address window (instruction fetch) and port B the DMEM
//          window (loads/stores); both windows alias the same physical
//          words, so the machine is von Neumann while fetch and data
//          traffic still proceed concurrently (different crossbar
//          slaves, different RAM ports).
//          WORDS is the memory size in 32-bit words (default 2^14 =
//          64 KiB). INIT_FILE is a $readmemh image of 32-bit words
//          applied at elaboration — synthesis-time initialization,
//          folded into the FPGA bitstream (built with scripts/mkmem.py
//          or rv32i.write_mem).
//          Same-cycle writes to the same word from both ports are
//          undefined, as in real BRAM.
// Author:  Ratko Pilipovic
// Date:    18 August 2026
///////////////////////////////////////////////////////////////////////

module obi_ram #(parameter ADDR_WIDTH = 14,      // words: 2^14 = 64 KiB
                 parameter INIT_FILE  = "") (
  input  logic        clk, reset,
  // OBI slave port A (instruction window)
  input  logic        ObiReqA,
  output logic        ObiGntA,
  input  logic [31:0] ObiAddrA,
  input  logic        ObiWeA,
  input  logic [3:0]  ObiBeA,
  input  logic [31:0] ObiWdataA,
  output logic        ObiRvalidA,
  output logic [31:0] ObiRdataA,
  // OBI slave port B (data window)
  input  logic        ObiReqB,
  output logic        ObiGntB,
  input  logic [31:0] ObiAddrB,
  input  logic        ObiWeB,
  input  logic [3:0]  ObiBeB,
  input  logic [31:0] ObiWdataB,
  output logic        ObiRvalidB,
  output logic [31:0] ObiRdataB);

  logic [ADDR_WIDTH-1:0] RamAddrA, RamAddrB;
  logic [31:0]           RamWdataA, RamWdataB, RamRdataA, RamRdataB;
  logic                  RamWeA, RamWeB;

  obi_ram_port #(ADDR_WIDTH) porta(
    .clk(clk), .reset(reset),
    .ObiReq(ObiReqA), .ObiGnt(ObiGntA), .ObiAddr(ObiAddrA), .ObiWe(ObiWeA),
    .ObiBe(ObiBeA), .ObiWdata(ObiWdataA), .ObiRvalid(ObiRvalidA), .ObiRdata(ObiRdataA),
    .RamAddr(RamAddrA), .RamWdata(RamWdataA), .RamWe(RamWeA), .RamRdata(RamRdataA));

  obi_ram_port #(ADDR_WIDTH) portb(
    .clk(clk), .reset(reset),
    .ObiReq(ObiReqB), .ObiGnt(ObiGntB), .ObiAddr(ObiAddrB), .ObiWe(ObiWeB),
    .ObiBe(ObiBeB), .ObiWdata(ObiWdataB), .ObiRvalid(ObiRvalidB), .ObiRdata(ObiRdataB),
    .RamAddr(RamAddrB), .RamWdata(RamWdataB), .RamWe(RamWeB), .RamRdata(RamRdataB));

  sync_dual_port_RAM #(.DATA_WIDTH(32), .ADDR_WIDTH(ADDR_WIDTH),
                       .INIT_FILE(INIT_FILE)) ram(
    .clock(clk),
    .addr_a(RamAddrA), .datain_a(RamWdataA), .we_a(RamWeA), .dataout_a(RamRdataA),
    .addr_b(RamAddrB), .datain_b(RamWdataB), .we_b(RamWeB), .dataout_b(RamRdataB));

endmodule
