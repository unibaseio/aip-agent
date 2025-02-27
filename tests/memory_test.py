# -*- coding: utf-8 -*-
"""
Unit tests for memory classes and functions
"""

import os
import unittest
from unittest.mock import patch, MagicMock

from aip_memory.message import Message
from aip_memory.buffered_memory import BufferedMemory
from aip_memory.serialize import serialize


class BufferedMemoryTest(unittest.TestCase):
    """
    Test cases for BufferedMemory
    """

    def setUp(self) -> None:
        self.memory = BufferedMemory(persistence_in_remote=True)
        self.file_name_1 = "tmp_mem_file1.txt"
        self.file_name_2 = "tmp_mem_file2.txt"
        self.Message_1 = Message("user", "Hello", role="user")
        self.Message_2 = Message(
            "agent",
            "Hello! How can I help you?",
            role="assistant",
            metadata="md"
        )
        self.Message_3 = Message(
            "user",
            "Translate the following sentence",
            role="assistant",
            metadata={"meta": "test"}
        )

        self.invalid = {"invalid_key": "invalid_value"}

    def tearDown(self) -> None:
        """Clean up before & after tests."""
        if os.path.exists(self.file_name_1):
            os.remove(self.file_name_1)
        if os.path.exists(self.file_name_2):
            os.remove(self.file_name_2)

    def test_add(self) -> None:
        """Test add different types of object"""
        # add Message
        self.memory.add(self.Message_1)
        self.assertEqual(
            self.memory.get(),
            [self.Message_1],
        )

        # add list
        self.memory.add([self.Message_2, self.Message_3])
        self.assertEqual(
            self.memory.get(),
            [self.Message_1, self.Message_2, self.Message_3],
        )

    @patch("loguru.logger.warning")
    def test_delete(self, mock_logging: MagicMock) -> None:
        """Test delete operations"""
        self.memory.add([self.Message_1, self.Message_2, self.Message_3])

        self.memory.delete(index=0)
        self.assertEqual(
            self.memory.get(),
            [self.Message_2, self.Message_3],
        )

        # test invalid
        self.memory.delete(index=100)
        mock_logging.assert_called_once_with(
            "Skip delete operation for the invalid index [100]",
        )

    def test_invalid(self) -> None:
        """Test invalid operations for memory"""
        # test invalid add
        with self.assertRaises(Exception) as context:
            self.memory.add(self.invalid)
        self.assertTrue(
            f"Cannot add {type(self.invalid)} to memory, must be a Message object."
            in str(context.exception),
        )

    def test_load_export(self) -> None:
        """
        Test load and export function of BufferedMemory
        """
        memory = BufferedMemory()
        user_input = Message(name="user", content="Hello", role="user")
        agent_input = Message(
            name="agent",
            content="Hello! How can I help you?",
            role="assistant",
        )
        memory.load([user_input, agent_input])
        retrieved_mem = memory.export(to_mem=True)
        self.assertEqual(
            retrieved_mem,
            [user_input, agent_input],
        )

        memory.export(file_path=self.file_name_1)
        memory.clear()
        self.assertEqual(
            memory.get(),
            [],
        )
        memory.load(self.file_name_1, True)
        self.assertEqual(
            serialize(memory.get()),
            serialize([user_input, agent_input]),
        )


if __name__ == "__main__":
    unittest.main()
