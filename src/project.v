module tt_um_sine_area_detector (

    input  wire [7:0] ui_in,//8位ADC码

    output wire [7:0] uo_out,//最终11位重合计数的低8位

    input  wire [7:0] uio_in,//uio[4:0]固定作为频率档位输入

    output wire [7:0] uio_out,//uio_out[7:5]输出结果高3位

    output wire [7:0] uio_oe,//uio[7:5]为结果输出；uio[4:0]为档位输入

    /* ena=1表示Tiny Tapeout已选中本项目 */
    input  wire       ena,//will go high when design is enabled

    input  wire       clk,//80 MHz

    input  wire       rst_n
);

    /* ADC转换成二值符号 */
    wire adc_sign;
    assign adc_sign = (ui_in >= 8'h80);

    /* 二进制频率档位：0~22 */
    reg [4:0] divider_exponent;
    reg       config_valid;

    always @* begin
        divider_exponent = uio_in[4:0];
        config_valid     = 1'b0;

        if (uio_in[4:0] <= 5'd22)
            config_valid = 1'b1;
    end

    wire overlap_bit;
    assign overlap_bit = adc_sign == square_wave;

    /* ena=0时锁存档位 */
    reg       config_latched_valid;
    reg [4:0] divider_exponent_latched;

    /*
     * 每2^档位个系统时钟产生一次sample_tick。
     */
    reg  [21:0] prescale_count;
    wire [22:0] prescale_terminal_extended;
    wire        sample_tick;

    assign prescale_terminal_extended =
        (23'd1 << divider_exponent_latched) - 23'd1;
    assign sample_tick =
        ({1'b0, prescale_count} == prescale_terminal_extended);

    /* 最近1600个重合样本中1的总数。 */
    reg        overlap_history [0:1599];
    reg [10:0] history_pointer;
    reg [10:0] valid_sample_count;
    reg [10:0] running_sum;
    reg        window_full;
    reg [10:0] overlap_result;
    /* 独立方波 */
    wire square_wave;
    assign square_wave = (history_pointer >= 11'd800);

    wire        oldest_overlap;
    wire [10:0] fill_sum_next;
    wire [10:0] slide_sum_next;

    assign oldest_overlap = overlap_history[history_pointer];
    assign fill_sum_next =
        running_sum + (overlap_bit ? 11'd1 : 11'd0);
    assign slide_sum_next =
        ( overlap_bit && !oldest_overlap) ? (running_sum + 11'd1) :
        (!overlap_bit &&  oldest_overlap) ? (running_sum - 11'd1) :
                                            running_sum;

    always @(posedge clk) begin
        if (!rst_n) begin
            config_latched_valid     <= 1'b0;
            divider_exponent_latched <= 5'd0;
            prescale_count           <= 22'd0;
            history_pointer          <= 11'd0;
            valid_sample_count       <= 11'd0;
            running_sum              <= 11'd0;
            window_full              <= 1'b0;
            overlap_result           <= 11'd0;
        
        end else if (ena) begin
            if (!config_latched_valid) begin
                prescale_count     <= 22'd0;
                history_pointer    <= 11'd0;
                valid_sample_count <= 11'd0;
                running_sum        <= 11'd0;
                window_full        <= 1'b0;

                if (config_valid) begin
                    divider_exponent_latched <= divider_exponent;
                    config_latched_valid     <= 1'b1;
                end else begin
                    divider_exponent_latched <= 5'd0;
                    config_latched_valid     <= 1'b0;
                end
            end else if (sample_tick) begin
                prescale_count <= 22'd0;

                /* 用当前样本覆盖指针所指的最旧样本，然后移动指针。 */
                overlap_history[history_pointer] <= overlap_bit;
                if (history_pointer == 11'd1599)
                    history_pointer <= 11'd0;
                else
                    history_pointer <= history_pointer + 11'd1;

                if (!window_full) begin
                    /* 前1600点为预热阶段，不读取尚未覆盖的旧存储内容。 */
                    running_sum <= fill_sum_next;

                    if (valid_sample_count == 11'd1599) begin
                        valid_sample_count <= 11'd1600;
                        window_full        <= 1'b1;
                        overlap_result     <= fill_sum_next;
                    end else begin
                        valid_sample_count <= valid_sample_count + 11'd1;
                    end
                end else begin
                    /* 窗口已满：加入新样本，同时移除1600点前的旧样本。 */
                    running_sum  <= slide_sum_next;
                    overlap_result <= slide_sum_next;
                end
            end else begin
                prescale_count <= prescale_count + 22'd1;
            end
        end else begin
            prescale_count     <= 22'd0;
            history_pointer    <= 11'd0;
            valid_sample_count <= 11'd0;
            running_sum        <= 11'd0;
            window_full        <= 1'b0;
        end
    end

    /* 11位重合计数为{uio_out[7:5], uo_out}。 */
    assign uo_out  = overlap_result[7:0];
    assign uio_out = {overlap_result[10:8], 5'b00000};
    assign uio_oe  = 8'b1110_0000;

endmodule
