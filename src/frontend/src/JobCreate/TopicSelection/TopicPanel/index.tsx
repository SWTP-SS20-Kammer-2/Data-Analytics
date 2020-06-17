import React from "react";
import {makeStyles, Button} from "@material-ui/core";

interface TopicPanelProps {
    topic: string;
    selectedTopic: string,
    selectTopicHandler: (topicName: string) => void;
}

const useStyles = makeStyles({
    panel: {
        display: "flex",
        justifyContent: "center",
        alignItems: "center",
        backgroundColor: "#2E97C5",
        color: "white",
        fontSize: "x-large",
        width: '100%',
        height: 80,
        transition: "0.2s",
        "&:hover": {
            border: "solid #00638D 5px",
            backgroundColor: "#2E97C5",
        },
    }
});

export const TopicPanel: React.FC<TopicPanelProps> = (props) => {
    const classes = useStyles();
    return (
        <Button
            className={classes.panel}
            style={props.topic === props.selectedTopic ? {border: "solid #00638D 7px"} : {border: ""}}
            onClick={() => {
                props.selectTopicHandler(props.topic);
            }
            }>
            {props.topic}
        </Button>
    )
};