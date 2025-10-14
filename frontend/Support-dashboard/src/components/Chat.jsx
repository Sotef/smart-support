const Chat = () => {
    return (
        <section className="chat">
        <div className="chat__header">
            <div>
            <h3>Rachel Jenkins</h3>
            <p>How can I get a refund?</p>
            </div>
            <button className="close-btn">Close Ticket</button>
        </div>

        <div className="chat__body">
            <div className="message message--client">
            <p>
                Good day, I need to know how the refund process works, I went
                through that section on your website but the instructions are so
                confusing. Thank you.
            </p>
            </div>

            <div className="message message--operator">
            <p>
                You have reached the Supportzen chatbot. My name is Yinka and I’ll
                be helping you out.
            </p>
            </div>
        </div>

        <div className="chat__input">
            <input type="text" placeholder="Type a message..." />
            <button className="send-btn">➤</button>
        </div>
        </section>
    );
};

export default Chat;
