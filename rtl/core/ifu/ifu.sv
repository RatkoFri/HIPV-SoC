///////////////////////////////////////////////////////////////////////
// ifu
//
// Purpose: Instruction Fetch Unit for the HIPV core (F stage).
//          Fetches instructions from memory over an OBI master port
//          (read-only subset: Req/Gnt address phase, Rvalid/Rdata
//          response phase, as on the CV32E40P instruction interface).
//          Holds the PC, computes PC+4 and selects the next PC
//          between the sequential address and the branch/jump target
//          resolved in the Execute stage.
//          The stage output (InstrF, PCF, PCPlus4F) is qualified by a
//          valid/ready handshake: ValidF marks a valid fetched
//          instruction, ReadyD is the Decode stage accepting it.
// Author:  Ratko Pilipovic
// Date:    10 August 2026
///////////////////////////////////////////////////////////////////////

module ifu (input  logic        clk, reset,
            // pipeline handshake and redirect
            input  logic        ReadyD,
            output logic        ValidF,
            input  logic        PCSrcE,
            input  logic [31:0] PCTargetE,
            // stage outputs to Decode
            output logic [31:0] InstrF,
            output logic [31:0] PCF, PCPlus4F,
            // OBI master port to instruction memory
            output logic        ObiReqF,
            input  logic        ObiGntF,
            output logic [31:0] ObiAddrF,
            input  logic        ObiRvalidF,
            input  logic [31:0] ObiRdataF);

  logic [31:0] PCNextF;
  logic        PCEnF, InstrEnF;

  // fetch control FSM
  ifuctrl ctrl(.clk(clk), .reset(reset), .ObiGntF(ObiGntF), .ObiRvalidF(ObiRvalidF),
               .ReadyD(ReadyD), .PCSrcE(PCSrcE), .ObiReqF(ObiReqF), .PCEnF(PCEnF),
               .InstrEnF(InstrEnF), .ValidF(ValidF));

  // next PC selection: sequential or redirect from Execute
  mux2 #(32)    pcmux(.D0(PCPlus4F), .D1(PCTargetE), .S(PCSrcE), .Y(PCNextF));

  // PC register
  flopenr #(32) pcreg(.clk(clk), .reset(reset), .en(PCEnF), .D(PCNextF), .Q(PCF));

  // sequential PC
  adder #(32)   pcadd4(.A(PCF), .B(32'd4), .Y(PCPlus4F));

  // fetched instruction register
  flopenr #(32) instrreg(.clk(clk), .reset(reset), .en(InstrEnF), .D(ObiRdataF), .Q(InstrF));

  // the OBI address is the current PC
  assign ObiAddrF = PCF;

endmodule
