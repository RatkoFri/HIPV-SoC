///////////////////////////////////////////////////////////////////////
// ifuctrl
//
// Purpose: Control FSM for the Instruction Fetch Unit.
//          One OBI transaction is outstanding at a time:
//            REQUEST   - drive ObiReqF, wait for ObiGntF
//            WAIT_RESP - wait for ObiRvalidF, capture the instruction
//            DONE      - present the instruction (ValidF) until the
//                        Decode stage takes it (ReadyD)
//          A redirect (PCSrcE) loads the PC with the branch target,
//          kills ValidF and marks any outstanding response as stale
//          (DiscardF) so it is dropped when it arrives.
//          Simplification: a redirect during REQUEST before ObiGntF
//          changes ObiAddrF while ObiReqF is high; a fully compliant
//          OBI master would keep the address phase stable.
// Author:  Ratko Pilipovic
// Date:    10 August 2026
///////////////////////////////////////////////////////////////////////

module ifuctrl (input  logic clk, reset,
                input  logic ObiGntF, ObiRvalidF, // From OBI memory
                input  logic ReadyD, PCSrcE,  // From Decode and Execute
                output logic ObiReqF, PCEnF, InstrEnF, ValidF);

  // 0. State type: enum logic [1:0] {REQUEST, WAIT_RESP, DONE}
  //    Signals: State, NextState, DiscardF

  // 1. State register (always_ff): reset -> REQUEST, else State <= NextState

  // 2. Next state logic (always_comb case (State))
  //      REQUEST:   ObiGntF ? WAIT_RESP : REQUEST
  //      WAIT_RESP: if ObiRvalidF: (DiscardF | PCSrcE) ? REQUEST : DONE
  //                 else stay in WAIT_RESP
  //      DONE:      (PCSrcE | ReadyD) ? REQUEST : DONE
  //      default:   REQUEST

  // 3. DiscardF: marks an outstanding response as stale (always_ff)
  //      reset              -> 0
  //      else if ObiRvalidF -> 0 (the stale response has arrived)
  //      else if PCSrcE while a transaction is outstanding
  //        (State == WAIT_RESP, or State == REQUEST and ObiGntF) -> 1

  // 4. Outputs
  //      ObiReqF  = in REQUEST
  //      PCEnF    = PCSrcE, or (in DONE and ReadyD)
  //      InstrEnF = in WAIT_RESP & ObiRvalidF & ~DiscardF & ~PCSrcE
  //      ValidF   = in DONE & ~PCSrcE

endmodule
