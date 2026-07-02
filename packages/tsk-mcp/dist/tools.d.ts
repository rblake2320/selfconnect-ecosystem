/**
 * TSK MCP tool definitions and handlers — exported for testing.
 * Uses @selfconnect/tsk-client API: key, vps, sessionStart, sessionEnd, event, getBudget
 */
export declare const TOOLS: ({
    name: string;
    description: string;
    inputSchema: {
        type: "object";
        properties: {
            session_id?: undefined;
            agent_id?: undefined;
            agent_type?: undefined;
            model?: undefined;
            event_type?: undefined;
            tool_name?: undefined;
            tokens_input?: undefined;
            tokens_output?: undefined;
            usd_cost?: undefined;
            events?: undefined;
        };
        required: never[];
    };
} | {
    name: string;
    description: string;
    inputSchema: {
        type: "object";
        properties: {
            session_id: {
                type: string;
                description: string;
            };
            agent_id: {
                type: string;
                description: string;
            };
            agent_type: {
                type: string;
                description: string;
            };
            model: {
                type: string;
                description: string;
            };
            event_type?: undefined;
            tool_name?: undefined;
            tokens_input?: undefined;
            tokens_output?: undefined;
            usd_cost?: undefined;
            events?: undefined;
        };
        required: string[];
    };
} | {
    name: string;
    description: string;
    inputSchema: {
        type: "object";
        properties: {
            session_id: {
                type: string;
                description: string;
            };
            event_type: {
                type: string;
                description: string;
            };
            agent_id: {
                type: string;
                description: string;
            };
            tool_name: {
                type: string;
                description: string;
            };
            tokens_input: {
                type: string;
                description: string;
            };
            tokens_output: {
                type: string;
                description: string;
            };
            usd_cost: {
                type: string;
                description: string;
            };
            agent_type?: undefined;
            model?: undefined;
            events?: undefined;
        };
        required: string[];
    };
} | {
    name: string;
    description: string;
    inputSchema: {
        type: "object";
        properties: {
            session_id: {
                type: string;
                description?: undefined;
            };
            events: {
                type: string;
                items: {
                    type: string;
                    properties: {
                        event_type: {
                            type: string;
                        };
                        agent_id: {
                            type: string;
                        };
                        tokens_input: {
                            type: string;
                        };
                        tokens_output: {
                            type: string;
                        };
                        usd_cost: {
                            type: string;
                        };
                    };
                    required: string[];
                };
            };
            agent_id?: undefined;
            agent_type?: undefined;
            model?: undefined;
            event_type?: undefined;
            tool_name?: undefined;
            tokens_input?: undefined;
            tokens_output?: undefined;
            usd_cost?: undefined;
        };
        required: string[];
    };
} | {
    name: string;
    description: string;
    inputSchema: {
        type: "object";
        properties: {
            session_id: {
                type: string;
                description?: undefined;
            };
            agent_id?: undefined;
            agent_type?: undefined;
            model?: undefined;
            event_type?: undefined;
            tool_name?: undefined;
            tokens_input?: undefined;
            tokens_output?: undefined;
            usd_cost?: undefined;
            events?: undefined;
        };
        required: string[];
    };
})[];
export declare function handleTool(name: string, args: Record<string, unknown>, tskKey: string): Promise<string>;
//# sourceMappingURL=tools.d.ts.map