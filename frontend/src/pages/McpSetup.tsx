import { Terminal, Shield, Cpu, HelpCircle, Code, Layers } from 'lucide-react'

export function McpSetup() {
    return (
        <div className="space-y-8">
            <div>
                <h2 className="text-2xl font-extrabold text-slate-800 tracking-tight flex items-center gap-2">
                    <Terminal className="w-6 h-6 text-indigo-500" /> Model Context Protocol (MCP) Setup
                </h2>
                <p className="text-xs text-slate-500 mt-1">
                    Bridge your developer utilities (like Claude Desktop or Cursor) to your local ATS Analyzer database engine.
                </p>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                {/* Main Guide */}
                <div className="lg:col-span-2 space-y-6">
                    <div className="bg-white border border-slate-200 rounded-3xl p-6 shadow-sm space-y-4">
                        <h3 className="font-bold text-slate-700 flex items-center gap-1.5 text-sm">
                            <Cpu className="w-4.5 h-4.5 text-indigo-500" /> How does it work?
                        </h3>
                        <p className="text-xs text-slate-600 leading-relaxed">
                            Model Context Protocol allows local AI assistant agents to safely perform tool calls on local workspace documents. By setting up the local MCP connection, you enable your external Claude Desktop or Cursor instance to run resume analysis and profile matching directly within its chat bar.
                        </p>
                    </div>

                    {/* Setup steps */}
                    <div className="bg-white border border-slate-200 rounded-3xl p-6 shadow-sm space-y-6">
                        <h3 className="font-bold text-slate-700 text-sm flex items-center gap-1.5">
                            <Code className="w-4.5 h-4.5 text-indigo-500" /> Connect to Claude Desktop
                        </h3>

                        <div className="text-xs space-y-3.5">
                            <p className="font-medium text-slate-655">
                                1. Open or create your Claude Desktop configuration file:
                            </p>
                            <div className="bg-slate-900 text-slate-300 p-3.5 rounded-xl font-mono text-[10px] space-y-1">
                                <p>%APPDATA%\Claude\claude_desktop_config.json</p>
                            </div>

                            <p className="font-medium text-slate-655">
                                2. Insert the following server tool configuration block into the <code>mcpServers</code> section:
                            </p>

                            <pre className="bg-slate-900 text-slate-350 p-4 rounded-xl font-mono text-[10px] overflow-x-auto leading-relaxed shadow-inner">
                                {`{
  "mcpServers": {
    "ats-analyzer-mcp": {
      "command": "python",
      "args": [
        "-m",
        "mcp_server.main"
      ],
      "env": {
        "PYTHONPATH": "E:\\\\PRJ1\\\\ats-analyzer",
        "DATABASE_URL": "sqlite:///E:\\\\PRJ1\\\\ats-analyzer\\\\backend\\\\app\\\\data\\\\db\\\\ats_analyzer.db",
        "OLLAMA_BASE_URL": "http://localhost:11434"
      }
    }
  }
}`}
                            </pre>

                            <p className="leading-relaxed text-slate-450 italic">
                                Note: Adjust file path directions to represent exact absolute layouts if your workspace is located in another directory drive.
                            </p>

                            <p className="font-medium text-slate-655 mt-4">
                                3. Completely close and restart your Claude Desktop app. You should see a new "plug" tool icon containing local ingestion capabilities.
                            </p>
                        </div>
                    </div>
                </div>

                {/* Side rules */}
                <div className="space-y-6">
                    <div className="bg-indigo-50/70 border border-indigo-550/10 rounded-2xl p-6 text-xs text-indigo-900 space-y-3">
                        <h4 className="font-bold flex items-center gap-1.5"><Layers className="w-4 h-4 text-indigo-650" /> Exposed Tools</h4>
                        <p className="leading-relaxed">
                            Once configured, the following agent tools become available to the LLM:
                        </p>
                        <ul className="list-disc pl-4 space-y-1.5 mt-2 font-mono text-[10px] text-slate-650">
                            <li>ingest_resume_file</li>
                            <li>ingest_linkedin_profile_file</li>
                            <li>query_compatibility_score</li>
                            <li>fetch_prioritized_recommendations</li>
                        </ul>
                    </div>
                </div>
            </div>
        </div>
    )
}
