///////////////////////////////////////////////////////////////////////
// mul
//
// Purpose: Multi-cycle multiplier for the Zmmul extension (mul, mulh,
//          mulhsu, mulhu), built around a single 16x16 unsigned
//          multiplier that computes one partial product per cycle.
//          Datapath only; the sequencing lives in mulctrl.
//
//          Interface contract (checked by tb/unit/mul):
//          - Start is a one-cycle pulse, asserted only while Busy = 0.
//            A, B and Funct3 are valid ONLY in the Start cycle; the
//            unit must capture whatever it needs from them.
//          - Busy is 1 from the cycle after Start until the result
//            has been acknowledged.
//          - Done = 1 means Result holds the final value. Done and
//            Result stay stable until Ack.
//          - Ack is asserted together with Done in the cycle the
//            result is consumed; the unit is idle again (Busy = 0)
//            in the next cycle.
//          - Done must rise at most 8 cycles after Start.
//
//          HW1 Task 2: replace the placeholder below with your
//          implementation. See docs/LectureNotes/HW1.md.
// Author:  <your name>
// Date:    <date>
///////////////////////////////////////////////////////////////////////

// placeholder: the inputs are unused until the unit is implemented
/* verilator lint_off UNUSEDSIGNAL */
module mul (input  logic        clk, reset,
            input  logic        Start, Ack,
            input  logic [31:0] A, B,
            input  logic [2:0]  Funct3,
            output logic        Busy, Done,
            output logic [31:0] Result);

  assign Busy   = 1'b0;
  assign Done   = 1'b0;
  assign Result = 32'b0;

endmodule
/* verilator lint_on UNUSEDSIGNAL */
