import React from "react";
import { ListItem, Divider, List, TextField, Button } from "@material-ui/core";
import { TopicPanel } from "./TopicPanel";
import { ContinueButton } from "../ContinueButton";
import { useStyles } from "../style";


export const TopicSelection: React.FC = () => {
    // const topics: string[] = useFetch("/topics");
    const classes = useStyles();
    const topics: string[] = ["Wettervorhersage: Deutschland", "Wettervorhersage: lokal", "Bundesliga-Ergebnisse"]
    const renderTopicPanel = (topic: string) => {
        return (
            <ListItem key={topic}>
                <TopicPanel topic={topic} />
                <Divider />
            </ListItem>
        );
    }
    return (
        <div>
            <List>
                {topics.map(t => renderTopicPanel(t))}
            </List>
            <Divider />
            <div className={classes.paddingSmall}>
                <TextField className={classes.inputField} variant="outlined" label="Job-Name"></TextField>
            </div>
        </div>
    );
};