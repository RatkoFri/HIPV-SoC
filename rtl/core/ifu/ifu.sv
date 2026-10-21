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

  // 0. Internal signals: PCNextF [31:0], PCEnF, InstrEnF

  // 1. Fetch control FSM: ifuctrl "ctrl"
  //    - inputs:  ObiGntF, ObiRvalidF, ReadyD, PCSrcE
  //    - outputs: ObiReqF, PCEnF, InstrEnF, ValidF

  // 2. Next PC: pcmux (mux2)
  //      PCSrcE = 0 -> PCPlus4F, PCSrcE = 1 -> PCTargetE  => PCNextF

  // 3. PC register: pcreg (flopenr #(32)), enable PCEnF, PCNextF -> PCF
  //    (reset value 0 = reset vector)

  // 4. Sequential PC: pcadd4 (adder #(32)), PCF + 32'd4 -> PCPlus4F

  // 5. Instruction register: instrreg (flopenr #(32)),
  //    enable InstrEnF, ObiRdataF -> InstrF

  // 6. OBI address is the current PC: ObiAddrF = PCF

endmodule
