///////////////////////////////////////////////////////////////////////
// hipv_soc
//
// Purpose: HIPV SoC top level. Connects the RV32I core's two OBI
//          masters (instruction fetch, data) through the OBI crossbar
//          to five slaves: the two windows of the unified dual-port
//          RAM, the UART, the timer and the GPIO.
//
//          Memory is one physical RAM behind two crossbar slaves: the
//          IMEM window (port A) and the DMEM window (port B) alias the
//          same words, so a single INIT_FILE image holds code and data
//          and loads can read rodata. See docs/MEMORY.md.
//
//          The crossbar boundary uses flattened packed vectors (the
//          coding standard does not allow arrays of signals as ports),
//          so master m occupies bit m / [m*32 +: 32] and slave s
//          likewise. hipv_soc_pkg supplies the indices.
//
//          The instruction master is read-only: its We/Be/Wdata are
//          tied off here.
// Author:  Ratko Pilipovic
// Date:    19 August 2026
///////////////////////////////////////////////////////////////////////

module hipv_soc
  import hipv_soc_pkg::*;
  #(parameter RAM_ADDR_WIDTH = 14,       // words: 2^14 = 64 KiB
    parameter INIT_FILE      = "",       // $readmemh image, synthesis-time
    parameter ARB_POLICY     = ARB_FIXED,
    parameter GPIO_WIDTH     = 8)
  (input  logic                   clk, reset,
   // UART pins
   output logic                   Tx,
   input  logic                   Rx,
   // GPIO pins
   input  logic [GPIO_WIDTH-1:0]  GpioIn,
   output logic [GPIO_WIDTH-1:0]  GpioOut,
   // timer compare match (future machine-timer interrupt)
   output logic                   TimerOverflow);

  // core masters
  logic        ObiIReq, ObiIGnt, ObiIRvalid;
  logic [31:0] ObiIAddr, ObiIRdata;
  logic        ObiDReq, ObiDGnt, ObiDWe, ObiDRvalid;
  logic [3:0]  ObiDBe;
  logic [31:0] ObiDAddr, ObiDWdata, ObiDRdata;

  // crossbar master side (flattened)
  logic [NUM_MASTERS-1:0]    MReq, MGnt, MWe, MRvalid;
  logic [NUM_MASTERS*32-1:0] MAddr, MWdata, MRdata;
  logic [NUM_MASTERS*4-1:0]  MBe;

  // crossbar slave side (flattened)
  logic [NUM_SLAVES-1:0]     SReq, SGnt, SWe, SRvalid;
  logic [NUM_SLAVES*32-1:0]  SAddr, SWdata, SRdata;
  logic [NUM_SLAVES*4-1:0]   SBe;

  // ---------------------------------------------------------------
  // core
  // ---------------------------------------------------------------
  hipv_core core(.clk(clk), .reset(reset),
                 .ObiIReq(ObiIReq), .ObiIGnt(ObiIGnt), .ObiIAddr(ObiIAddr),
                 .ObiIRvalid(ObiIRvalid), .ObiIRdata(ObiIRdata),
                 .ObiDReq(ObiDReq), .ObiDGnt(ObiDGnt), .ObiDAddr(ObiDAddr),
                 .ObiDWe(ObiDWe), .ObiDBe(ObiDBe), .ObiDWdata(ObiDWdata),
                 .ObiDRvalid(ObiDRvalid), .ObiDRdata(ObiDRdata));

  // ---------------------------------------------------------------
  // master ports into the crossbar
  // ---------------------------------------------------------------
  assign MReq[MASTER_D]              = ObiDReq;
  assign MAddr[MASTER_D*32 +: 32]    = ObiDAddr;
  assign MWe[MASTER_D]               = ObiDWe;
  assign MBe[MASTER_D*4 +: 4]        = ObiDBe;
  assign MWdata[MASTER_D*32 +: 32]   = ObiDWdata;
  assign ObiDGnt                     = MGnt[MASTER_D];
  assign ObiDRvalid                  = MRvalid[MASTER_D];
  assign ObiDRdata                   = MRdata[MASTER_D*32 +: 32];

  assign MReq[MASTER_I]              = ObiIReq;
  assign MAddr[MASTER_I*32 +: 32]    = ObiIAddr;
  assign MWe[MASTER_I]               = 1'b0;      // fetch never writes
  assign MBe[MASTER_I*4 +: 4]        = 4'b1111;
  assign MWdata[MASTER_I*32 +: 32]   = 32'b0;
  assign ObiIGnt                     = MGnt[MASTER_I];
  assign ObiIRvalid                  = MRvalid[MASTER_I];
  assign ObiIRdata                   = MRdata[MASTER_I*32 +: 32];

  // ---------------------------------------------------------------
  // interconnect
  // ---------------------------------------------------------------
  obi_xbar #(.NUM_MASTERS(NUM_MASTERS), .NUM_SLAVES(NUM_SLAVES),
             .ARB_POLICY(ARB_POLICY)) xbar(
    .clk(clk), .reset(reset),
    .MReq(MReq), .MGnt(MGnt), .MAddr(MAddr), .MWe(MWe), .MBe(MBe),
    .MWdata(MWdata), .MRvalid(MRvalid), .MRdata(MRdata),
    .SReq(SReq), .SGnt(SGnt), .SAddr(SAddr), .SWe(SWe), .SBe(SBe),
    .SWdata(SWdata), .SRvalid(SRvalid), .SRdata(SRdata));

  // ---------------------------------------------------------------
  // unified memory: IMEM window on port A, DMEM window on port B
  // ---------------------------------------------------------------
  obi_ram #(.ADDR_WIDTH(RAM_ADDR_WIDTH), .INIT_FILE(INIT_FILE)) mem(
    .clk(clk), .reset(reset),
    .ObiReqA(SReq[SLAVE_IMEM]), .ObiGntA(SGnt[SLAVE_IMEM]),
    .ObiAddrA(SAddr[SLAVE_IMEM*32 +: 32]), .ObiWeA(SWe[SLAVE_IMEM]),
    .ObiBeA(SBe[SLAVE_IMEM*4 +: 4]), .ObiWdataA(SWdata[SLAVE_IMEM*32 +: 32]),
    .ObiRvalidA(SRvalid[SLAVE_IMEM]), .ObiRdataA(SRdata[SLAVE_IMEM*32 +: 32]),
    .ObiReqB(SReq[SLAVE_DMEM]), .ObiGntB(SGnt[SLAVE_DMEM]),
    .ObiAddrB(SAddr[SLAVE_DMEM*32 +: 32]), .ObiWeB(SWe[SLAVE_DMEM]),
    .ObiBeB(SBe[SLAVE_DMEM*4 +: 4]), .ObiWdataB(SWdata[SLAVE_DMEM*32 +: 32]),
    .ObiRvalidB(SRvalid[SLAVE_DMEM]), .ObiRdataB(SRdata[SLAVE_DMEM*32 +: 32]));

  // ---------------------------------------------------------------
  // peripherals
  // ---------------------------------------------------------------
  uart uart(.clk(clk), .reset(reset),
            .ObiReq(SReq[SLAVE_UART]), .ObiGnt(SGnt[SLAVE_UART]),
            .ObiAddr(SAddr[SLAVE_UART*32 +: 32]), .ObiWe(SWe[SLAVE_UART]),
            .ObiBe(SBe[SLAVE_UART*4 +: 4]),
            .ObiWdata(SWdata[SLAVE_UART*32 +: 32]),
            .ObiRvalid(SRvalid[SLAVE_UART]),
            .ObiRdata(SRdata[SLAVE_UART*32 +: 32]),
            .Tx(Tx), .Rx(Rx));

  timer timer(.clk(clk), .reset(reset),
              .ObiReq(SReq[SLAVE_TIMER]), .ObiGnt(SGnt[SLAVE_TIMER]),
              .ObiAddr(SAddr[SLAVE_TIMER*32 +: 32]), .ObiWe(SWe[SLAVE_TIMER]),
              .ObiBe(SBe[SLAVE_TIMER*4 +: 4]),
              .ObiWdata(SWdata[SLAVE_TIMER*32 +: 32]),
              .ObiRvalid(SRvalid[SLAVE_TIMER]),
              .ObiRdata(SRdata[SLAVE_TIMER*32 +: 32]),
              .Overflow(TimerOverflow));

  gpio #(.NUM_IN(GPIO_WIDTH), .NUM_OUT(GPIO_WIDTH)) gpio(
    .clk(clk), .reset(reset),
    .ObiReq(SReq[SLAVE_GPIO]), .ObiGnt(SGnt[SLAVE_GPIO]),
    .ObiAddr(SAddr[SLAVE_GPIO*32 +: 32]), .ObiWe(SWe[SLAVE_GPIO]),
    .ObiBe(SBe[SLAVE_GPIO*4 +: 4]), .ObiWdata(SWdata[SLAVE_GPIO*32 +: 32]),
    .ObiRvalid(SRvalid[SLAVE_GPIO]), .ObiRdata(SRdata[SLAVE_GPIO*32 +: 32]),
    .GpioIn(GpioIn), .GpioOut(GpioOut));

endmodule
