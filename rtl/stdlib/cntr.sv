module cntr #(
    parameter int WORD_WIDTH = 32,
    parameter logic [WORD_WIDTH-1:0] RESET_VALUE = 0
)(
    input  logic clk,
    input  logic rstn,
    input  logic clear,
    input  logic ce,
    output logic [WORD_WIDTH-1:0] count
);
    logic [WORD_WIDTH-1:0] plus_one;
    register_wclear #(
        .DTYPE(logic [WORD_WIDTH-1:0]),
        .RESET_VALUE(RESET_VALUE)
    ) rvfi_order_reg (
        .clk  (clk),
        .rstn (rstn),
        .clear(clear),
        .ce   (ce),
        .in   (plus_one),
        .out  (count)
    );
    assign plus_one = count + 1'b1;
endmodule
