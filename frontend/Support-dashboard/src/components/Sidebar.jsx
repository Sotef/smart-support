const Sidebar = () => {
    return (
        <aside className="sidebar">
        <h2 className="sidebar__title">Tickets</h2>

        <div className="ticket">
            <h4>How can I get a refund?</h4>
            <p>Good day, I need to know how the refund process works...</p>
        </div>

        <div className="ticket active">
            <h4>My card got declined</h4>
            <p>Good morning, card declined and I need to...</p>
        </div>

        <div className="ticket">
            <h4>Can I get up to 90% discount?</h4>
            <p>I’ve bought at least 50 items this month...</p>
        </div>

        <div className="ticket">
            <h4>Your checkout process is awful</h4>
            <p>Hi, I’m a box of chiv balls from your app...</p>
        </div>
        </aside>
    );
};

export default Sidebar;
