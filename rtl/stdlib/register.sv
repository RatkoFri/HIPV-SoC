module register
#(
    parameter type DTYPE = logic,
    parameter DTYPE RESET_VALUE = 0
)
(
    input  logic clk,
    input  logic rstn,
    input  logic ce,   // clock-enable
    input  DTYPE in,
    output DTYPE out
);

    // HIPV: synchronous reset (upstream std-lib uses an asynchronous one:
    // `always_ff @(posedge clk or negedge rstn)`). The project coding
    // standard requires synchronous reset throughout; rstn stays
    // active-low so no instantiation in the peripheral cores changes.
    always_ff @(posedge clk) begin
        if (~rstn)
            out <= RESET_VALUE;
        else if (ce)
            out <= in;
    end
endmodule
