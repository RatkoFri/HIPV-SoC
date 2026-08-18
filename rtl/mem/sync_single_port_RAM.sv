// Single-port synchronous RAM, 1-cycle read latency, read-first on
// write. Not used by the SoC; kept as a teaching primitive.
//
// Fixes vs the original upload: parameter list moved after the module
// name, trailing comma in the port list removed, `inital` -> `initial`,
// INIT_FILE parameter.

module sync_single_port_RAM #(
    parameter DATA_WIDTH = 8,
    parameter ADDR_WIDTH = 8,
    parameter INIT_FILE  = ""
) (
    input logic clock,
    input logic [ADDR_WIDTH-1:0] addr_a,
    input logic [DATA_WIDTH-1:0] datain_a,
    input logic we_a,
    output logic [DATA_WIDTH-1:0] dataout_a
);

    logic [DATA_WIDTH-1:0] mem [0:2**ADDR_WIDTH-1];
    logic [DATA_WIDTH-1:0] data_a;

    always_ff @(posedge clock) begin
        if (we_a) begin
            mem[addr_a] <= datain_a;
        end
        data_a <= mem[addr_a];
    end

    assign dataout_a = data_a;

    initial begin
        if (INIT_FILE != "") $readmemh(INIT_FILE, mem);
    end

endmodule
