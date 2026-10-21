///////////////////////////////////////////////////////////////////////
// lsu
//
// Purpose: Load/Store Unit for the HIPV core (M stage).
//          Holds the E/M pipeline register. Non-memory instructions
//          pass through in one cycle. Loads and stores run one OBI
//          transaction on the data port (req/gnt, rvalid/rdata with
//          we/be/wdata for stores); the stage presents ValidM only
//          when the transaction is complete, so ReadyM back-pressures
//          the Execute stage during the access.
//          Byte/halfword accesses are aligned with byte enables and
//          the read data is shifted and sign/zero extended by funct3.
//          ForwardDataM feeds the forwarding mux in Execute: the load
//          data for loads, the ALU result otherwise.
//          Misaligned accesses are not detected (no traps yet).
// Author:  Ratko Pilipovic
// Date:    10 August 2026
///////////////////////////////////////////////////////////////////////

module lsu (input  logic        clk, reset,
            // handshake with the Execute stage
            input  logic        ValidE,
            output logic        ReadyM,
            // inputs from Execute
            input  logic [31:0] ALUResultE, WriteDataE, PCPlus4E,
            input  logic [4:0]  RdE,
            input  logic [2:0]  Funct3E,
            input  logic        RegWriteE, MemWriteE,
            input  logic [1:0]  ResultSrcE,
            // handshake with the Writeback stage
            output logic        ValidM,
            input  logic        ReadyW,
            // stage outputs to Writeback
            output logic [31:0] ALUResultM, ReadDataM, PCPlus4M,
            output logic [4:0]  RdM,
            output logic        RegWriteM,
            output logic [1:0]  ResultSrcM,
            // forwarding to Execute
            output logic [31:0] ForwardDataM,
            // OBI master port to data memory
            output logic        ObiReqM,
            input  logic        ObiGntM,
            output logic [31:0] ObiAddrM,
            output logic        ObiWeM,
            output logic [3:0]  ObiBeM,
            output logic [31:0] ObiWdataM,
            input  logic        ObiRvalidM,
            input  logic [31:0] ObiRdataM);

  // 0. import hipv_pkg::* (RESULT_MEM)
  //    Internal signals:
  //      ValidMReg, EnEM, MemOpM, DoneM, WaitRespM, CaptureM
  //      RegWriteMReg, MemWriteM, Funct3M [2:0], AddrLsbM [1:0]
  //      WriteDataM, ReadRawM, ReadShiftM [31:0]

  // 1. E/M handshake: a memory instruction holds the stage until done
  //    - MemOpM = store (MemWriteM) or load (ResultSrcM == RESULT_MEM)
  //    - ValidM = ValidMReg & (not a memory op, or DoneM)
  //    - ReadyM = stage empty, or (ValidM & ReadyW)
  //    - EnEM   = ValidE & ReadyM

  // 2. E/M valid bit ValidMReg (always_ff): reset 0, else if ReadyM take ValidE

  // 3. E/M pipeline registers (flopenr, enable EnEM)
  //      alureg     #(32) ALUResultE -> ALUResultM
  //      wdreg      #(32) WriteDataE -> WriteDataM
  //      pcplus4reg #(32) PCPlus4E   -> PCPlus4M
  //      rdreg      #(5)  RdE        -> RdM
  //      funct3reg  #(3)  Funct3E    -> Funct3M
  //      ctrlreg    #(4)  {RegWriteE, MemWriteE, ResultSrcE}
  //                    -> {RegWriteMReg, MemWriteM, ResultSrcM}

  // 4. OBI transaction control, one outstanding request per instruction
  //    - ObiReqM  = ValidMReg & MemOpM & ~DoneM & ~WaitRespM
  //    - CaptureM = WaitRespM & ObiRvalidM
  //    - WaitRespM (always_ff): reset 0; set on ObiReqM & ObiGntM
  //      (when not already waiting); clear on CaptureM
  //    - DoneM (always_ff): reset 0; clear when a new instruction
  //      enters (EnEM); set on CaptureM

  // 5. Raw read data register: rawreg (flopenr #(32)),
  //    enable CaptureM, ObiRdataM -> ReadRawM

  // 6. Address phase
  //    - AddrLsbM  = ALUResultM[1:0]
  //    - ObiAddrM  = word-aligned address (low 2 bits zero)
  //    - ObiWeM    = MemWriteM
  //    - ObiWdataM = WriteDataM shifted left by AddrLsbM bytes ({AddrLsbM, 3'b000})
  //    - ObiBeM by access size Funct3M[1:0]:
  //        00 byte (sb/lb): 4'b0001 << AddrLsbM
  //        01 half (sh/lh): AddrLsbM[1] ? 4'b1100 : 4'b0011
  //        else word:       4'b1111

  // 7. Read data alignment and extension
  //    - ReadShiftM = ReadRawM shifted right by AddrLsbM bytes
  //    - ReadDataM by Funct3M:
  //        000 lb:  sign-extend byte      001 lh:  sign-extend halfword
  //        100 lbu: zero-extend byte      101 lhu: zero-extend halfword
  //        default lw: ReadShiftM

  // 8. ForwardDataM = load data (ReadDataM) for loads, else ALUResultM

  // 9. RegWriteM = RegWriteMReg qualified with ValidMReg

endmodule
