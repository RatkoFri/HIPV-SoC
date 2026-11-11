///////////////////////////////////////////////////////////////////////
// mulctrl
//
// Purpose: Control unit for mul: IDLE -> BUSY (four steps, one
//          partial product each) -> DONE, back to IDLE on Ack.
// Author:  HW1 reference solution
// Date:    6 October 2026
///////////////////////////////////////////////////////////////////////

module mulctrl (input  logic       clk, reset,
                input  logic       Start, Ack,
                output logic       Busy, Done, AccEn,
                output logic [1:0] Step);

  typedef enum logic [1:0] {IDLE, BUSY, DONE} statetype;

  statetype State, NextState;

  // state register
  always_ff @(posedge clk)
    if (reset) State <= IDLE;
    else State <= NextState;

  // step counter: selects the operand halves and the shift
  always_ff @(posedge clk)
    if (reset | Start) Step <= 2'b00;
    else if (State == BUSY) Step <= Step + 2'b01;

  // next state logic
  always_comb
    case (State)
      IDLE:    NextState = Start ? BUSY : IDLE;
      BUSY:    NextState = (Step == 2'b11) ? DONE : BUSY;
      DONE:    NextState = Ack ? IDLE : DONE;
      default: NextState = IDLE;
    endcase

  assign Busy  = (State != IDLE);
  assign Done  = (State == DONE);
  assign AccEn = (State == BUSY);

endmodule
