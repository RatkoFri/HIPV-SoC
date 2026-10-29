
module mux4to1(
    input logic [3:0] I,
    input logic [1:0] S,
    output logic O
    );
    // block executes whenever any of the 
    // input signals of block changes 
    
    always_comb begin : MUX
        case (S)
            2'b00 : O = I[0]; 
            2'b01 : O = I[1]; 
            2'b10 : O = I[2]; 
            2'b11 : O = I[3]; 
            default: O = 1'b0; 
        endcase
    end

endmodule 
