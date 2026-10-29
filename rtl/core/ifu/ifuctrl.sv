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
//          State and DiscardF are both held in the same current/next
//          pair, so the decision in WAIT_RESP is taken on the current
//          DiscardF while its clear is scheduled for the next cycle.
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

  // 0. State type: typedef enum logic [1:0] {REQUEST, WAIT_RESP, DONE} statetype
  //    Signals: State, NextState (statetype); DiscardF, NextDiscardF (logic)



  // 1. State register (always_ff), holds both State and DiscardF:
  //      reset -> State = REQUEST, DiscardF = 0
  //      else  -> State <= NextState, DiscardF <= NextDiscardF
  

  // 2. Next state logic (always_comb case (State))
  //      defaults: NextState = State, NextDiscardF = DiscardF (hold)
  //      REQUEST:   NextState    = ObiGntF ? WAIT_RESP : REQUEST
  //                 NextDiscardF = ObiGntF & PCSrcE
  //                   (the grant commits the transaction on this edge, so a
  //                    redirect in the same cycle already has a wrong-path
  //                    response coming)
  //      WAIT_RESP: if ObiRvalidF: NextState    = (DiscardF | PCSrcE) ? REQUEST : DONE
  //                                NextDiscardF = 0 (the awaited response arrived)
  //                 else:          NextDiscardF = DiscardF | PCSrcE
  //                                (a redirect makes the outstanding response stale)
  //      DONE:      if (PCSrcE | ReadyD) NextState = REQUEST
 

  // 3. Outputs
  //      ObiReqF  = in REQUEST
  //      PCEnF    = PCSrcE, or (in DONE and ReadyD)
  //      InstrEnF = in WAIT_RESP & ObiRvalidF & ~DiscardF & ~PCSrcE
  //      ValidF   = in DONE & ~PCSrcE



endmodule
