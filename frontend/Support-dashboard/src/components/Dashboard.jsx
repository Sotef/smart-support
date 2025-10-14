import Sidebar from "./Sidebar";
import Chat from "./Chat";
import Leaderboard from "./Leaderboard";

const Dashboard = () => {
    return (
        <>
            <div className="dashboard">
                <Sidebar />
                <Chat />
                <Leaderboard />
            </div>
        </>    
    );
};

export default Dashboard;
