import os
from decimal import Decimal
import json
import requests

import streamlit as st
import pandas as pd


# Set the title and favicon that appear in the Browser's tab bar.
st.set_page_config(
    page_title="Bushido Karate Resource Library",
    page_icon=":martial_arts_uniform:",
)


def fetch_data_from_api(api_url: str):
    """Fetches inventory data from the API Gateway endpoint.

    Expects the Lambda to return a JSON array of items with columns:
    id, item_name, type, description, on_loan, rating
    """
    try:
        resp = requests.get(api_url, timeout=10)
        resp.raise_for_status()
        payload = resp.json()
        # payload can be {'body': '...'} when proxied through API Gateway v1; try to normalize
        if isinstance(payload, dict) and "body" in payload and isinstance(payload["body"], str):
            try:
                payload = json.loads(payload["body"])
            except Exception:
                # leave as-is
                pass

        df = pd.DataFrame(payload)
        # If Dynamo stored number types as Decimal, convert them
        for col in df.columns:
            if df[col].apply(lambda x: isinstance(x, (Decimal,))).any():
                df[col] = df[col].apply(lambda x: float(x) if isinstance(x, Decimal) else x)

        return df
    except Exception as e:
        st.error(f"Failed to fetch data from API: {e}")
        return pd.DataFrame(columns=["id", "item_name", "type", "description", "on_loan", "rating"])


def main():
    st.title(":martial_arts_uniform: Bushido Karate Resource Library")

    st.markdown(
        """
        Browse the club's resource inventory. The app loads data from an API Gateway endpoint
        which proxies a Lambda that reads from DynamoDB.
        """
    )

    # Detect API URL from env or ask the user
    api_url = os.environ.get("API_GATEWAY_URL", "")
    api_url = st.text_input("API Gateway URL", value=api_url)

    if not api_url:
        st.info("Enter the API Gateway GET URL (for example: https://<id>.execute-api.<region>.amazonaws.com/prod/inventory)")
        return

    df = fetch_data_from_api(api_url)

    if df is None or df.empty:
        st.info("No data available from the API yet.")
        return

    # Show an editable table for browsing (local edits do not write back to DynamoDB in this example)
    st.data_editor(
        df,
        disabled=["id"],
        num_rows="fixed",
        key="inventory_table",
    )

    st.markdown("---")
    # Simple UI to toggle on_loan status
    ids = df["id"].tolist()
    selected_id = st.selectbox("Select item id to toggle loan status", options=ids)
    current = df.loc[df["id"] == selected_id, "on_loan"].iloc[0]
    st.write(f"Current on_loan: {current}")

    if st.button("Toggle loan status"):
        new_status = not bool(current)
        try:
            resp = requests.post(api_url, json={"id": int(selected_id), "on_loan": new_status}, timeout=10)
            resp.raise_for_status()
            st.success("Updated")
            # record in session history
            if "changes_history" not in st.session_state:
                st.session_state["changes_history"] = []
            st.session_state["changes_history"].append({
                "id": int(selected_id),
                "old": bool(current),
                "new": bool(new_status),
                "when": __import__("datetime").datetime.utcnow().isoformat() + "Z",
            })
            # refresh
            df = fetch_data_from_api(api_url)
            st.experimental_rerun()
        except Exception as e:
            st.error(f"Failed to update: {e}")


if __name__ == "__main__":
    main()

    # show history if available
    if "changes_history" in st.session_state and st.session_state["changes_history"]:
        st.markdown("## Update history")
        st.table(pd.DataFrame(st.session_state["changes_history"]))
