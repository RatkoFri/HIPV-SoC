
module counter (
    input clk,
    output pulse
)

    logic [31:0] counter;
    always_ff @( posedge clk ) begin : blockName
        counter <= counter + 1; 
        if (counter==100e6) begin
            pulse = 1'b1;
            counter = 1'b0;
        end else begin
            pulse = 1'b0;
        end
    end

endmodule