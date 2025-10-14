const Leaderboard = () => {
    const leaders = [
        { name: "Akin Majekodunmi", score: 301 },
        { name: "Lola Ifeanyichukwu", score: 289 },
        { name: "Corrine Amadi", score: 280 },
        { name: "Faraz Abubakar", score: 278 },
        { name: "Majorie Etim", score: 270 },
        { name: "Ifeoluwa Subair", score: 240 },
    ];

    return (
        <aside className="leaderboard">
        <h2>Leaderboard 🏅</h2>
        <div className="leaderboard__list">
            {leaders.map((leader, index) => (
            <div className="leaderboard__item" key={index}>
                <span className="rank">#{index + 1}</span>
                <div className="leader-info">
                <p className="name">{leader.name}</p>
                <p className="score">{leader.score} issues solved</p>
                </div>
            </div>
            ))}
        </div>
        </aside>
    );
};

export default Leaderboard;
