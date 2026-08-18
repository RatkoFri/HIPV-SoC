///////////////////////////////////////////////////////////////////////
// obi_ram_port
//
// Purpose: OBI slave controller for one port of the synchronous RAM —
//          the buffer between the bus and the raw memory port. The
//          request (address, write data, byte enables) is captured at
//          grant, so the bus is released while the RAM completes.
//          Timing:
//            read       : grant, RAM read issued        -> rvalid (2 cy)
//            word write : grant, RAM written            -> rvalid (2 cy)
//            sb/sh      : grant + read, merge + write   -> rvalid (3 cy)
//          Sub-word stores are read-modify-write: the RAM primitive
//          has no byte enables, so the old word is read, the enabled
//          bytes are merged in, and the word is written back.
//          The port assumes the fabric behaviour: one outstanding
//          transaction, responses always accepted.
// Author:  Ratko Pilipovic
// Date:    18 August 2026
///////////////////////////////////////////////////////////////////////

module obi_ram_port #(parameter ADDR_WIDTH = 14) (
  input  logic                  clk, reset,
  // OBI slave port
  input  logic                  ObiReq,
  output logic                  ObiGnt,
  // only the word-index bits of the window are used; the bits above
  // the window and the byte offset are legitimately ignored
  /* verilator lint_off UNUSEDSIGNAL */
  input  logic [31:0]           ObiAddr,
  /* verilator lint_on UNUSEDSIGNAL */
  input  logic                  ObiWe,
  input  logic [3:0]            ObiBe,
  input  logic [31:0]           ObiWdata,
  output logic                  ObiRvalid,
  output logic [31:0]           ObiRdata,
  // RAM port (word addressed, 1-cycle read latency)
  output logic [ADDR_WIDTH-1:0] RamAddr,
  output logic [31:0]           RamWdata,
  output logic                  RamWe,
  input  logic [31:0]           RamRdata);

  typedef enum logic [1:0] {IDLE, RMW, RESP} statetype;

  statetype    State, NextState;
  logic [ADDR_WIDTH-1:0] AddrQ;
  logic [31:0] WdataQ, ByteMaskQ;
  logic        SubWordQ;
  logic        AcceptQ;   // transaction captured this cycle

  assign AcceptQ = ObiReq & ObiGnt;

  // state register
  always_ff @(posedge clk)
    if (reset) State <= IDLE;
    else State <= NextState;

  // next state logic
  always_comb
    case (State)
      IDLE:    if (~AcceptQ) NextState = IDLE;
               else if (ObiWe & (ObiBe != 4'b1111)) NextState = RMW;
               else NextState = RESP;
      RMW:     NextState = RESP;
      default: NextState = IDLE;  // RESP: response always accepted
    endcase

  // request capture (the buffer)
  always_ff @(posedge clk)
    if (AcceptQ) begin
      AddrQ     <= ObiAddr[ADDR_WIDTH+1:2];
      WdataQ    <= ObiWdata;
      ByteMaskQ <= {{8{ObiBe[3]}}, {8{ObiBe[2]}}, {8{ObiBe[1]}}, {8{ObiBe[0]}}};
      SubWordQ  <= ObiWe & (ObiBe != 4'b1111);
    end

  // RAM port drive
  //  IDLE: present the live address; write immediately for full-word
  //        stores, read otherwise (data for loads, old word for RMW)
  //  RMW : write back the merged word
  always_comb
    if (State == IDLE) begin
      RamAddr  = ObiAddr[ADDR_WIDTH+1:2];
      RamWdata = ObiWdata;
      RamWe    = AcceptQ & ObiWe & (ObiBe == 4'b1111);
    end else begin
      RamAddr  = AddrQ;
      RamWdata = (RamRdata & ~ByteMaskQ) | (WdataQ & ByteMaskQ);
      RamWe    = (State == RMW);
    end

  // OBI handshake
  assign ObiGnt    = (State == IDLE);
  assign ObiRvalid = (State == RESP);
  assign ObiRdata  = SubWordQ ? 32'b0 : RamRdata;

endmodule
