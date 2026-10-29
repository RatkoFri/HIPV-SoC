module dff(
    input logic clk,
    input logic rst,
    input logic en,
    input logic D,
    output logic Q
  );
    // block executes on every positive edge of clk
    // sensitivity list is refered after @ sign 
    
    always_ff @( posedge clk ) begin : DFF
      if (rst) begin
        Q <= 1'b0;
      end else begin
        if (en) begin
          Q <= D; 
        end
      end
      
    end
    
  endmodule 