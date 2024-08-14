import React from 'react';

const LeftAlignedTable = ({ type, required }) => {
    return (
        <div style={{ textAlign: 'left' }}>
            <table style={{ marginLeft: 0 }}>
                <tbody>
                    <tr>
                        <td>Type</td>
                        <td><code>{type}</code></td>
                    </tr>
                    <tr>
                        <td>Required</td>
                        <td><b>{required ? 'Yes' : 'No'}</b></td>
                    </tr>
                </tbody>
            </table>
            <br />
        </div>
    );
};

export default LeftAlignedTable;
