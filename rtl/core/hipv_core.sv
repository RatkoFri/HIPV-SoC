///////////////////////////////////////////////////////////////////////
// hipv_core
//
// Purpose: HIPV top level: 5-stage pipelined RV32I core.
//          Connects the pipeline stages (ifu, idu, ieu, lsu, wbu) via
//          valid/ready handshakes and the hazard unit (forwarding).
//          Two OBI master ports: instruction fetch (read-only) and
//          data (read/write).
// Author:  Ratko Pilipovic
// Date:    10 August 2026
///////////////////////////////////////////////////////////////////////

module hipv_core (input  logic        clk, reset,
                  // OBI instruction port
                  output logic        ObiIReq,
                  input  logic        ObiIGnt,
                  output logic [31:0] ObiIAddr,
                  input  logic        ObiIRvalid,
                  input  logic [31:0] ObiIRdata,
                  // OBI data port
                  output logic        ObiDReq,
                  input  logic        ObiDGnt,
                  output logic [31:0] ObiDAddr,
                  output logic        ObiDWe,
                  output logic [3:0]  ObiDBe,
                  output logic [31:0] ObiDWdata,
                  input  logic        ObiDRvalid,
                  input  logic [31:0] ObiDRdata);

  // 1. Declare the signals between the stages, grouped by stage boundary
  //    F <-> D:   ValidF, ReadyD
  //               InstrF, PCF, PCPlus4F                        [31:0]
  //    D <-> E:   ValidD, ReadyE
  //               RD1D, RD2D, ImmExtD, PCD, PCPlus4D           [31:0]
  //               Rs1D, Rs2D, RdD                              [4:0]
  //               Funct3D                                      [2:0]
  //               RegWriteD, MemWriteD, BranchD, JumpD, JalrD, ALUSrcBD
  //               ResultSrcD, ALUSrcAD                         [1:0]
  //               ALUControlD                                  [3:0]
  //    E <-> M:   ValidE, ReadyM
  //               ALUResultE, WriteDataE, PCPlus4E             [31:0]
  //               RdE, Rs1E, Rs2E                              [4:0]
  //               Funct3E                                      [2:0]
  //               RegWriteE, MemWriteE
  //               ResultSrcE                                   [1:0]
  //    redirect:  PCSrcE, PCTargetE [31:0]
  //    M <-> W:   ValidM, ReadyW
  //               ALUResultM, ReadDataM, PCPlus4M, ForwardDataM [31:0]
  //               RdM [4:0], RegWriteM, ResultSrcM [1:0]
  //    W outputs: ValidW (retirement marker, unused: wrap its declaration
  //               in a lint_off/lint_on UNUSEDSIGNAL pair), RegWriteW,
  //               RdW [4:0], ResultW [31:0]
  //    hazard:    ForwardAE, ForwardBE                         [1:0]
  
  // 2. Fetch: ifu "ifu"
  //    - handshake ReadyD/ValidF, redirect PCSrcE/PCTargetE
  //    - outputs InstrF, PCF, PCPlus4F
  //    - OBI ports Obi*F connect to the core ObiI* ports

  // 3. Decode: idu "idu"
  //    - from F: ValidF/ReadyD, InstrF, PCF, PCPlus4F; flush PCSrcE
  //    - to E: ValidD/ReadyE and all *D signals
  //    - register file write port from W: RegWriteW, RdW, ResultW

  // 4. Execute: ieu "ieu"
  //    - from D: ValidD/ReadyE and all *D signals
  //    - forwarding: ForwardAE, ForwardBE, ForwardDataM, ResultW
  //    - redirect out: PCSrcE, PCTargetE
  //    - to M: ValidE/ReadyM and all *E signals (incl. Rs1E, Rs2E for hazard)

  // 5. Memory: lsu "lsu"
  //    - from E: ValidE/ReadyM, ALUResultE, WriteDataE, PCPlus4E, RdE,
  //      Funct3E, RegWriteE, MemWriteE, ResultSrcE
  //    - to W: ValidM/ReadyW, ALUResultM, ReadDataM, PCPlus4M, RdM,
  //      RegWriteM, ResultSrcM
  //    - ForwardDataM back to Execute
  //    - OBI ports Obi*M connect to the core ObiD* ports

  // 6. Writeback: wbu "wbu"
  //    - from M: ValidM/ReadyW and the *M signals
  //    - outputs ValidW, RegWriteW, RdW, ResultW

  // 7. Hazard unit: hazard "hz"
  //    - Rs1E, Rs2E, RdM, RdW, RegWriteM, RegWriteW -> ForwardAE, ForwardBE

endmodule
